# ADR-0004: Хранение auth credentials на клиентах

Статус: принято для web; native adapter реализован через secure-storage plugin.

Web/PWA: access token только в памяти; refresh token доставляется HttpOnly/Secure/SameSite cookie, JavaScript его не читает. Native: access token в памяти, refresh token — `@aparajita/capacitor-secure-storage`, использующий системное защищённое хранилище. `localStorage` не используется для auth credentials.
