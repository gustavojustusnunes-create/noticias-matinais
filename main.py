name: Briefing Diário

on:
  schedule:
    - cron: '0 10 * * *' # Roda todo dia às 07:00 Brasil
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Baixar código
        uses: actions/checkout@v3

      - name: Instalar Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'  # ATUALIZADO PARA 3.11

      - name: Instalar dependências
        run: pip install -r requirements.txt

      - name: Rodar Robô
        env:
          GEMINI_KEY: ${{ secrets.GEMINI_KEY }}
          EMAIL_USER: ${{ secrets.EMAIL_USER }}
          EMAIL_PASSWORD: ${{ secrets.EMAIL_PASSWORD }}
        run: python main.py
