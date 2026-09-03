#!/usr/bin/env python3
"""Сервер эхлүүлэх цэг:  python run.py

Deploy дээр Procfile-аар uvicorn шууд ажиллана. Энэ файл нь локал хөгжүүлэлт,
эсвэл `web: python run.py` маягийн энгийн start command-д зориулагдсан.
Аль ч тохиолдолд 0.0.0.0:8000 дээр сонсоно (127.0.0.1 бол гаднаас нээгдэхгүй).
"""
import os
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", 8000)),
        reload=os.environ.get("RELOAD", "0") == "1",
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
