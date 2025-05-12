import json

with open("backend/Services/gestao-de-contratos-459115-56094189aaf9.json", "r") as f:
    raw = f.read()

# apenas serializa sem alterar \n
env_string = raw.strip().replace("\n", "\\n")  # cuidado com newlines
with open(".env", "w", encoding="utf-8") as f:
    f.write(f'GDRIVE_CREDENTIALS_JSON={env_string}\n')

print("✅ .env criado no formato correto (sem json.dumps)")
