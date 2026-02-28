@echo off
title SIDEKICK CRM - Starting...
echo.
echo  =============================================
echo        SIDEKICK Enterprise CRM
echo        Starting application...
echo  =============================================
echo.

call myenv\Scripts\activate
streamlit run app.py --server.port 8501 --server.headless true

pause
