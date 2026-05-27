@echo off
title Iniciando Monitoramento Camerite V3
cls

cd /d "C:\Users\FernandoHenriqueSofi\Desktop\Monitoramento"

echo Iniciando o Streamlit...
streamlit run monitoramento_V3.py --server.port 8686 --server.address 0.0.0.0

pause