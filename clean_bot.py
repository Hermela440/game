# Script to clean null bytes from bot.py
with open("bot.py", "rb") as f:
    data = f.read()

clean_data = data.replace(b'\x00', b'')

with open("bot_cleaned.py", "wb") as f:
    f.write(clean_data)

print("Cleaning complete. Check bot_cleaned.py") 