# I-0 — Capacitor technical spike

Статус: **частично выполнен; device validation остаётся обязательной перед закрытием I-0**.

## Что проверено в рамках автономной реализации

Клиент зафиксирован на Capacitor 8 и содержит foundation/кандидаты для обязательных capabilities:

| Capability | Foundation / candidate | Статус в этой среде |
|---|---|---|
| secure storage | `@aparajita/capacitor-secure-storage` | adapter реализован; native runtime не запускался |
| SQLite | `@capacitor-community/sqlite` | dependency зафиксирована; device runtime не запускался |
| camera | `@capacitor/camera` | dependency зафиксирована; device runtime не запускался |
| GPS | `@capacitor/geolocation` | dependency зафиксирована; device runtime не запускался |
| push | `@capacitor/push-notifications` | dependency зафиксирована; credentials/device runtime не доступны |
| background execution | `@capacitor/background-runner` | candidate зафиксирован; OS kill/recovery не проверены |
| MapLibre | `maplibre-gl` | dependency зафиксирована; native WebView/offline tiles не проверены |
| media upload/resume | HTTP/application-level mechanism | реализация media domain вне I-0; native interruption test не выполнен |

## Что нельзя достоверно проверить в текущей среде

Среда автономного выполнения не предоставляет Android SDK/emulator, Xcode/iOS simulator, физические устройства, APNs/FCM/RuStore credentials и возможность воспроизводить OS kill/background ограничения. Поэтому нельзя утверждать, что следующие пункты прошли acceptance test:

- background sync после сворачивания приложения;
- восстановление фоновой операции после OS kill;
- push delivery на Android/iOS;
- реальная Keychain/Keystore запись и восстановление после restart;
- SQLite/SQLCipher на реальном устройстве;
- MapLibre + offline tiles в native WebView;
- camera/GPS permission lifecycle;
- resumable media upload при потере сети.

## Обязательная device matrix перед merge/закрытием I-0

Минимум один поддерживаемый Android 9+ device/emulator и один iOS 15+ device/simulator. Для каждого пункта выше записать: OS/device, plugin version, шаги, observed result, ограничения. OS-kill проверки предпочтительно выполнять на физическом Android и iPhone, потому что simulator/emulator не полностью воспроизводят ограничения фонового исполнения.

## Вывод

Архитектурный риск не замаскирован: persistence/token abstractions и зависимости заложены, но device-dependent часть spike остаётся явным blocking item для формального Definition of Done I-0.


## Что требуется от владельца проекта для закрытия blocker

Чтобы формально закрыть device-dependent часть I-0, от владельца проекта требуется предоставить среду, которую нельзя эмулировать в автономном cloud-runner.

### Android

Минимально:

- рабочая станция с Node.js 22+;
- Android Studio 2025.2.1+;
- Android SDK / target SDK 36;
- физическое Android-устройство, соответствующее целевой поддержке проекта (Android 9+);
- USB debugging или wireless debugging;
- доступ устройства к test/stage backend по HTTPS.

Допустимо сначала выполнить smoke-check на emulator, но проверки background execution, network interruption и OS kill должны быть подтверждены на физическом устройстве.

### iOS

Минимально:

- macOS;
- Xcode 26.0+;
- iOS 15+ simulator для базового smoke-check;
- предпочтительно физический iPhone для background/OS-kill и Keychain lifecycle;
- доступ устройства к test/stage backend по HTTPS.

Если Mac/Xcode/iOS runtime недоступны, iOS-часть spike остаётся открытой и I-0 формально нельзя считать полностью закрытой по принятому Definition of Done.

### Push

Для проверки реальной доставки push нужны credentials/configuration целевой push-инфраструктуры:

- Android: FCM или выбранный для production эквивалент;
- iOS: APNs.

Без credentials можно проверить только регистрацию plugin/permission lifecycle, но не end-to-end delivery.

## Порядок device validation

1. Поднять отдельный test/stage backend по HTTPS.
2. Собрать web bundle с `VITE_API_BASE_URL`, указывающим на этот backend.
3. Выполнить `npx cap add android` / `npx cap add ios` при отсутствии native project.
4. Выполнить `npx cap sync <platform>`.
5. Установить приложение на target device.
6. Пройти обычный I-0 flow: стартовый экран -> регистрация -> OTP -> dashboard -> logout -> login.
7. Выполнить capability matrix ниже.
8. Для каждого теста записать device/OS, plugin version, steps, observed result и ограничения.
9. Приложить логи/скриншоты только там, где они помогают подтвердить результат; секреты, токены и ПДн в evidence не включать.
10. После прохождения матрицы обновить этот документ со статусом `passed/failed/limited` по каждой capability.

## Acceptance matrix

| Capability | Минимальная проверка для закрытия |
|---|---|
| Secure storage | записать test secret -> полностью закрыть приложение -> открыть -> прочитать -> logout/remove -> убедиться, что secret удалён |
| SQLite | создать локальную БД/таблицу -> записать запись -> restart -> прочитать запись; отдельно проверить поведение после app upgrade/build replacement без uninstall |
| Camera | запрос permission -> сделать фото -> получить файл/URI -> cancel path -> denied permission path |
| GPS | запрос permission -> получить координаты -> denied permission path -> повторный запуск после изменения permission в OS settings |
| MapLibre | открыть карту в native WebView -> pan/zoom -> проверить отсутствие render crash |
| Offline tiles | предварительно сохранить тестовый набор -> включить airplane mode -> открыть заранее сохранённую область |
| Background execution | запустить тестовую background operation -> свернуть приложение -> подтвердить выполнение/ограничение ОС |
| OS kill/recovery | начать recoverable operation -> force-stop/kill -> открыть приложение -> проверить восстановление или корректное сохранённое состояние |
| Push | permission -> получить registration token -> отправить test push -> проверить foreground/background delivery |
| Media upload/resume | начать достаточно большой upload -> оборвать сеть -> восстановить сеть -> подтвердить resume/retry без дубля результата |
| Network reconnect | войти -> отключить сеть -> вернуть сеть -> подтвердить восстановление API/session без ручного reset |

## Что остаётся подготовить в коде перед полной device matrix

Текущий production UI I-0 намеренно не содержит диагностических controls для camera/GPS/SQLite/background/push/media/offline tiles. Поэтому для воспроизводимого spike нужен отдельный development-only diagnostic harness либо временные native test cases.

Diagnostic harness не должен попадать в production navigation и не должен использовать реальные пользовательские ПДн. После device validation его можно удалить или оставить как internal development tooling отдельным ADR/решением.

## Критерий закрытия внешнего blocker

Blocker закрыт, когда:

- Android matrix пройдена на физическом Android-устройстве;
- iOS базовая matrix пройдена на iOS runtime, а background/OS-kill/Keychain проверены на физическом iPhone либо явно принято отдельное решение о допустимости simulator-only проверки;
- реальная push delivery проверена с целевой push-инфраструктурой либо push вынесен отдельным согласованным исключением из I-0;
- результаты записаны в этом документе;
- не осталось capability со статусом `unknown`.

Официальные требования Capacitor 8 к окружению: https://capacitorjs.com/docs/getting-started/environment-setup
