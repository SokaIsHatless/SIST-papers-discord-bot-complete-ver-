
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
#import sqlite3
import aiosqlite # for the add paper command
import os 
import time
from dotenv import load_dotenv

#from requests import options
# Initialize the bot



# Documentation and comments added to explain the logic
# This bot uses discord.py to provide GPA and CGPA calculation functionality.
# It integrates SQLite for storing course data and uses slash commands for user interaction.
# Key features include:
# - Adding courses to the database
# - Calculating GPA for a semester
# - Calculating CGPA across multiple semesters
# - A user-friendly modal for grade entry

# Ensure to replace "YOUR_BOT_TOKEN" with your actual bot token before running the bot.

#from requests import options
# Initialize the bot

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='soka', intents=intents)





DB_PATH = "papers.db"
PAPER_FOLDER = "papers"

os.makedirs(PAPER_FOLDER, exist_ok=True)

async def setup_database():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS papers(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_code TEXT,
            course_name TEXT,
            semester INTEGER,
            exam_type TEXT,
            file_path TEXT
        )
        """)

        # Add batch column if not exists
        try:
            await db.execute("ALTER TABLE papers ADD COLUMN batch TEXT")
            print("Batch column added.")
        except aiosqlite.OperationalError as e:
            if "duplicate column name" in str(e):
                print("Batch column already exists.")
            else:
                raise

        

        # SPEED IMPROVEMENT INDEXES
        await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_course_exam
        ON papers(course_code, exam_type)
        """)

        await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_course_code
        ON papers(course_code)
        """)

        await db.commit()

# Custom view for displaying papers with pagination and selection for the /find_paper command. It shows a dropdown of papers and buttons to navigate through pages of results.
class PaperSelect(discord.ui.Select):

    def __init__(self, papers, page, course_code, exam_type):
        self.papers = papers
        self.page = page
        self.course_code = course_code
        self.exam_type = exam_type

        start = page * 25
        end = start + 25

        options = []

        for i, paper in enumerate(papers[start:end], start=start):
            course_name, sem, batch, _ = paper

            options.append(
                discord.SelectOption(
                    label=f"Sem {sem} | {exam_type} | {batch}",
                    description=course_name,
                    value=str(i)
                )
            )

        if not options:
            options.append(
                discord.SelectOption(
                    label="No papers available",
                    value="0"
                )
             )

        super().__init__(
        placeholder="Select a paper to download",
        options=options
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        index = int(self.values[0]) 

        course_name, sem, batch, file_path = self.papers[index]

        if not os.path.exists(file_path):
            await interaction.followup.send("❌ File missing from server.", ephemeral=True)
            return
        await interaction.followup.send(
            "📥 Sending paper... before we send subscribe to Soka Xd",
            ephemeral=True
        )
        await interaction.followup.send(
            content=f"{self.course_code} | {course_name} | Sem {sem} | {self.exam_type} | Batch {batch}",
            file=discord.File(file_path),
            ephemeral=True
        )


class PaperView(discord.ui.View):

    def __init__(self, papers, course_code, exam_type, page=0):
        super().__init__(timeout=120)

        self.papers = papers
        self.course_code = course_code
        self.exam_type = exam_type
        self.page = page

        self.total_pages = (len(papers) - 1) // 25

        self.add_item(PaperSelect(papers, page, course_code, exam_type))


    @discord.ui.button(label="⬅ Previous", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):

        if self.page == 0:
            await interaction.response.defer()
            return

        self.page -= 1  

        view = PaperView(self.papers, self.course_code, self.exam_type, self.page)

        await interaction.response.edit_message(
            content=f"📄 Page {self.page+1}/{self.total_pages+1}",
            view=view
        )


    @discord.ui.button(label="Next ➡", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):

        if self.page >= self.total_pages:
            await interaction.response.defer()
            return

        self.page += 1

        view = PaperView(self.papers, self.course_code, self.exam_type, self.page)

        await interaction.response.edit_message(
            content=f"📄 Page {self.page+1}/{self.total_pages+1}",
            view=view
        )

# Autocomplete function for course code input in the /find_paper command. It queries the database for distinct course codes that match the current input and returns them as choices for autocomplete.
# The following is a function definition for the autocomplete feature of the course code input in the /find_paper command. It queries the database for distinct course codes that match the current input and returns them as choices for autocomplete.
async def course_code_autocomplete(
    interaction: discord.Interaction,
    current: str
):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT DISTINCT course_code
            FROM papers
            WHERE course_code LIKE ?
            LIMIT 25
            """,
            (f"%{current}%",)
        ) as cursor:
            rows = await cursor.fetchall()

    return [
        app_commands.Choice(name=row[0], value=row[0])
        for row in rows
    ]
# This thing gets the bot ready and syncs the commands to the server. It also sets up the database when the bot is ready.
@bot.event
async def on_ready():
    await setup_database()
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

    print(f"Logged in as {bot.user}")

# Command for adding a new question paper to the database. Only admins can use this command. It takes the subject code, course title, exam name, year, and a PDF file as input.
@bot.tree.command(name="add_paper", description="Upload question paper (Admin only)")
@app_commands.describe(
    course_name="Course name",
    course_code="Course code",
    semester="Semester number (1-8)",
    exam_type="CAE1 / CAE2 / ENDSEM",
    file="Upload PDF file",
    batch="Batch"
)
@app_commands.choices(
    exam_type=[
        app_commands.Choice(name="CAE1", value="CAE1"),
        app_commands.Choice(name="CAE2", value="CAE2"),
        app_commands.Choice(name="ENDSEM", value="ENDSEM")
    ],
    batch=[
        app_commands.Choice(name="2024-2027", value="2024-2027"),
        app_commands.Choice(name="2024-2028", value="2024-2028"),
        app_commands.Choice(name="2024-2029", value="2024-2029"),
        app_commands.Choice(name="2025-2028", value="2025-2028"),
        app_commands.Choice(name="2025-2029", value="2025-2029"),
        app_commands.Choice(name="2025-2030", value="2025-2030"),
    ]
)
async def add_paper(
    interaction: discord.Interaction,
    course_name: str,
    course_code: str,
    semester: int,
    exam_type: app_commands.Choice[str],
    file: discord.Attachment,
    batch: app_commands.Choice[str]
):
    course_code = course_code.upper()
    course_name = course_name.title()

    await interaction.response.defer(ephemeral=True)

    if not interaction.user.guild_permissions.administrator:
        await interaction.followup.send(
            "❌ Only administrators can upload papers.",
            ephemeral=True
        )
        return

    # Read file
    file_bytes = await file.read()

    # Validate PDF
    if (
        not file.filename.lower().endswith(".pdf")
        or file.content_type != "application/pdf"
        or not file_bytes.startswith(b"%PDF")
    ):
        await interaction.followup.send(
            "❌ Only valid PDF files allowed.",
            ephemeral=True
        )
        return

    # Create folders FIRST
    course_folder = os.path.join(PAPER_FOLDER, course_code)
    exam_folder = os.path.join(course_folder, exam_type.value)
    os.makedirs(exam_folder, exist_ok=True)

    # Create file path
    file_name = f"{course_code}_SEM{semester}_{batch.value}_{int(time.time())}.pdf"
    file_path = os.path.join(exam_folder, file_name)

    # Save file (ONLY ONCE)
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # Save to DB
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO papers (course_code, course_name, semester, exam_type, file_path, batch) VALUES (?, ?, ?, ?, ?, ?)",
            (
                course_code,
                course_name,
                semester,
                exam_type.value,
                file_path,
                batch.value
            )
        )
        await db.commit()

    await interaction.followup.send(
        "✅ Paper uploaded successfully!",
        ephemeral=True
    )

# Command for searching previous year question papers based on subject code, year, and exam name. It returns the matching papers as attachments in the response.
@bot.tree.command(name="find_paper", description="Search question papers")
@app_commands.describe(
    course_code="Course code",
    exam_type="CAE1 / CAE2 / ENDSEM",
    semester="Semester number (optional)",
    batch="Batch (optional)"
)
@app_commands.autocomplete(course_code=course_code_autocomplete)
@app_commands.choices(
    exam_type=[
        app_commands.Choice(name="CAE1", value="CAE1"),
        app_commands.Choice(name="CAE2", value="CAE2"),
        app_commands.Choice(name="ENDSEM", value="ENDSEM")
    ],
    batch=[
        app_commands.Choice(name="2024-2027", value="2024-2027"),
        app_commands.Choice(name="2024-2028", value="2024-2028"),
        app_commands.Choice(name="2024-2029", value="2024-2029"),
        app_commands.Choice(name="2025-2028", value="2025-2028"),
        app_commands.Choice(name="2025-2029", value="2025-2029"),
        app_commands.Choice(name="2025-2030", value="2025-2030"),
    ]
)
async def find_paper(
    interaction: discord.Interaction,
    course_code: str,
    exam_type: app_commands.Choice[str],
    semester: int = None,
    batch: app_commands.Choice[str] = None
):

    query = """
        SELECT course_name, semester, batch, file_path
        FROM papers
        WHERE course_code = ?
        AND exam_type = ?
    """

    params = [course_code, exam_type.value]

    if semester is not None:
        query += " AND semester = ?"
        params.append(semester)

    if batch is not None:
        query += " AND batch = ?"
        params.append(batch.value)

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(query, params) as cursor:
            results = await cursor.fetchall()

    if not results:
        await interaction.response.send_message(
            "❌ No papers found.",
            ephemeral=True
        )
        return

    view = PaperView(results, course_code, exam_type.value)

    await interaction.response.send_message(
        f"📄 Page 1/{(len(results)-1)//25 + 1}",
        view=view,
        ephemeral=True
    )

# Command to list all stored question papers in the database. It returns a formatted list of papers with course code, course name, semester, and exam type.
@bot.tree.command(name="list_papers", description="List all stored question papers")
async def list_papers(interaction: discord.Interaction):

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ Only administrators can use this command.",
            ephemeral=True
        )
        return

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT course_code, course_name, semester, exam_type, batch FROM papers"
        ) as cursor:
            results = await cursor.fetchall()

    if not results:
        await interaction.response.send_message(
            "📂 No papers found in database.",
            ephemeral=True
        )
        return

    # Build file content
    content = "📚 LIST OF STORED QUESTION PAPERS\n\n"
    content += f"Total Papers: {len(results)}\n\n"

    for row in results:
        course_code, course_name, semester, exam_type, batch = row
        content += (
            f"{course_code} | {course_name} | "
            f"Semester {semester} | {exam_type} | Batch: {batch}\n"
        )

    file_name = "paper_list.txt"

    with open(file_name, "w", encoding="utf-8") as f:
        f.write(content)

    await interaction.response.send_message(
        file=discord.File(file_name),
        ephemeral=True
    )

    os.remove(file_name)

# Command to delete a specific paper from the database. It prompts the admin to select which paper to delete from a list of matching papers based on course code, exam type, and optional semester. The selected paper is then removed from the database and the file is deleted from storage.
@bot.tree.command(name="delete_paper", description="Safely delete a specific paper (Admin only)")
@app_commands.describe(
    course_code="Course code",
    exam_type="CAE1 / CAE2 / ENDSEM",
    semester="Semester number (optional)"
)
@app_commands.autocomplete(course_code=course_code_autocomplete)
@app_commands.choices(
    exam_type=[
        app_commands.Choice(name="CAE1", value="CAE1"),
        app_commands.Choice(name="CAE2", value="CAE2"),
        app_commands.Choice(name="ENDSEM", value="ENDSEM")
    ]
)
async def delete_paper(
    interaction: discord.Interaction,
    course_code: str,
    exam_type: app_commands.Choice[str],
    semester: int = None
):

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ Only administrators can delete papers.",
            ephemeral=True
        )
        return

    query = """
        SELECT id, course_name, semester, batch, file_path
        FROM papers
        WHERE course_code = ?
        AND exam_type = ?
    """
    params = [course_code, exam_type.value]

    if semester is not None:
        query += " AND semester = ?"
        params.append(semester)

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(query, params) as cursor:
            results = await cursor.fetchall()

    if not results:
        await interaction.response.send_message(
            "❌ No matching papers found.",
            ephemeral=True
        )
        return

    # Build numbered list
    paper_list = ""
    for index, row in enumerate(results, start=1):
        paper_id, course_name, sem, batch_value, _ = row
        paper_list += f"{index}. {course_code} | {course_name} | Sem {sem} | {exam_type.value} | Batch: {batch_value}\n"

    await interaction.response.send_message(
        f"Select the number of the paper to delete:\n\n{paper_list}\n"
        "Type the number in chat within 30 seconds.",
        ephemeral=True
    )

    await interaction.channel.send(f"{interaction.user.mention}, enter the number of the paper to delete.")

    def check(m):
        return (
            m.author.id == interaction.user.id
            and m.channel.id == interaction.channel.id
            and m.content.isdigit()
        )

    try:
        msg = await bot.wait_for("message", timeout=30.0, check=check)
        selection = int(msg.content)

        if selection < 1 or selection > len(results):
            await interaction.followup.send( 
                "❌ Invalid selection.",
                ephemeral=True
            )
            return

        paper_id, _, _, _,  file_path = results[selection - 1]

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM papers WHERE id = ?", (paper_id,))
            await db.commit()

        if os.path.exists(file_path):
            os.remove(file_path)

        await interaction.followup.send(
            "🗑 Paper deleted successfully.",
            ephemeral=True
        )

    except asyncio.TimeoutError:
        await interaction.followup.send(
            "⌛ Deletion timed out.",
            ephemeral=True
        )

#command to list all available courses in the database. It queries for distinct course codes and names and returns them in a formatted message. If the message exceeds Discord's character limit, it sends the list as a text file attachment instead.
@bot.tree.command(name="courses", description="List all available courses along with their codes")
async def list_courses(interaction: discord.Interaction):

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT DISTINCT course_code, course_name
            FROM papers
            ORDER BY course_code
        """) as cursor:
            results = await cursor.fetchall()

    if not results:
        await interaction.response.send_message(
            "❌ No courses found.",
            ephemeral=True
        )
        return

    content = "📚 Available Courses\n\n"

    for code, name in results:
        content += f"{code} - {name}\n"

    # If message too long, send as file
    if len(content) > 1900:
        with open("courses.txt", "w", encoding="utf-8") as f:
            f.write(content)

        await interaction.response.send_message(
            file=discord.File("courses.txt"),
            ephemeral=True
        )

        os.remove("courses.txt")
    else:
        await interaction.response.send_message(
            content,
            ephemeral=True
        )



# Running the bot
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
bot.run(TOKEN)

# Documentation and comments added to explain the logic
# This bot uses discord.py to provide GPA and CGPA calculation functionality.
# It integrates SQLite for storing course data and uses slash commands for user interaction.
# Key features include:
# - Adding courses to the database
# - Calculating GPA for a semester
# - Calculating CGPA across multiple semesters
# - A user-friendly modal for grade entry

# Ensure to replace "YOUR_BOT_TOKEN" with your actual bot token before running the bot.