# Jaguar Interface Frontend

Bu proje, Jaguar robot kontrol arayüzünün frontend kısmını içerir. React.js ile geliştirilmiştir.

## Kurulum

1. Projeyi klonlayın:
```bash
git clone https://github.com/your-repo/jaguar-interface.git
```

2. Frontend dizinine gidin ve bağımlılıkları yükleyin:
```bash
cd jaguar-interface/frontend
npm install
```

3. Geliştirme sunucusunu başlatın:
```bash
npm run start
```

## Kullanılan Teknolojiler

- React.js
- Axios (API istekleri için)
- React Router (Navigasyon için)

## Ana Sayfalar

- **Dashboard:** Robotun genel durumunu gösterir
- **Debug Panel:** Robotun detaylı kontrolünü sağlar

## API Entegrasyonu

Frontend, backend ile REST API üzerinden iletişim kurar. API base URL'i:
```javascript
export const API_BASE_URL = 'http://192.168.43.80:5000';
```