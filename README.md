# SIST Paper Discord Bot 📚
A Discord bot that allows students to access and download previous year question papers directly from Discord.
Features

📥 Upload Papers — Admins can upload question papers as PDFs
🔍 Find Papers — Search for papers by course code, exam type, semester, and batch
📋 List Papers — View all stored papers in the database
🗑️ Delete Papers — Admins can safely delete specific papers

Commands:
1/add_paper: Upload a question paper (PDF)Admin only
2)/find_paper: Search and download question papersEveryone
3)/list_papers: List all stored papers Admin only
4)/delete_paper: Delete a specific paperAdmin only

Tech Stack:
Python
discord.py
SQLite / aiosqlite


Notes:
Only PDF files are accepted for uploads
Only server administrators can upload, list, or delete papers
All paper interactions are ephemeral (only visible to the user)
Note to self: have to update this properly later
