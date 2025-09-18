# Hướng dẫn sửa lỗi Google Sign-in

## 🔧 Các vấn đề đã sửa:

### 1. API Configuration
- ✅ Sửa `main.py` để sử dụng đúng API server
- ✅ Tạo `.env.example` với GOOGLE_CLIENT_ID từ Firebase

### 2. Flutter Google Sign-in
- ✅ Tạo `GoogleSignInService` trong `lib/data/api/google.dart`
- ✅ Cập nhật `login_screen.dart` để sử dụng service mới

### 3. Google Client ID
- ✅ Tìm thấy GOOGLE_CLIENT_ID: `992932679265-hpmc2gu7aju6kfv685bt2ksfav0usd2n.apps.googleusercontent.com`

## 📋 Cần làm thêm:

### 1. Tạo file .env cho API
```bash
# Copy .env.example và cập nhật các giá trị:
cp .env.example .env
```

Cập nhật file .env với:
- `GEMINI_API_KEY=your_actual_key`
- `JWT_SECRET_KEY=your_secure_secret`
- `GOOGLE_CLIENT_ID=992932679265-hpmc2gu7aju6kfv685bt2ksfav0usd2n.apps.googleusercontent.com`

### 2. Khởi động lại API
```bash
cd chatbot-rhm-api
python start_api.py
```

### 3. Kiểm tra Flutter debug
```bash
cd chatbot-rhm-mobile
flutter clean
flutter pub get
flutter run
```

## 🐛 Debug Tips:

### Kiểm tra logs:
- Android Studio Logcat
- Flutter console: `flutter logs`
- API logs khi chạy local

### Các lỗi thường gặp:
1. **"Invalid Google token"** → Kiểm tra GOOGLE_CLIENT_ID trong API
2. **"Network Error"** → Kiểm tra baseUrl trong constants.dart
3. **"Sign-in failed"** → Kiểm tra google-services.json và package name

### Kiểm tra kết nối API:
```bash
curl https://denti-chatbot.hiaivn.com/api/docs
```

## 📱 Android Configuration
- ✅ Package name: `com.example.chatbox`
- ✅ Google Services plugin enabled
- ✅ google-services.json có đúng client IDs

## 🔍 Next Steps:
1. Chạy Flutter app
2. Test Google sign-in
3. Check console logs nếu có lỗi
