#!/bin/bash

# Python ve npm yollarını kontrol et
if ! command -v python3 &> /dev/null; then
    echo "Python3 bulunamadı. Lütfen Python3'ü yükleyin."
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "npm bulunamadı. Lütfen npm'yi yükleyin."
    exit 1
fi

# Proje kök dizini
PROJECT_ROOT=$(pwd)/
export PYTHONPATH=$PYTHONPATH:$PROJECT_ROOT

# Backend'i başlat (arka plan) ve PID'yi al
cd backend
python3 run.py &
FLASK_PID=$!

# Ctrl+C algılandığında Flask'ı öldür
trap "echo 'Kapatılıyor...'; kill $FLASK_PID; exit 0" SIGINT

# Frontend'i başlat
cd ../frontend

# node_modules yoksa npm install'i çalıştır
if [ ! -d "node_modules" ]; then
    echo "node_modules bulunamadı. Bağımlılıklar yükleniyor..."
    npm install
fi

npm start

# npm start bittiğinde backend'i de kapat
kill $FLASK_PID
