# Дизайн-система для ИИ-агентов

> Файл-памятка для LLM-агентов (Claude, GPT и др.), которые верстают HTML/CSS-лендинги в "Песочнице".
> Фокус: продуктовые / B2B-лендинги (фичи, для бизнеса, для продавцов).

---

## 1. Логотип

### Доступные варианты
- Основной логотип Flowwow (B2C).
- Логотип Flowwow Seller (для B2B-материалов).

### Правила использования
| Правило | Значение |
|---|---|
| Высота на лендинге | `30px` |
| Охранные поля | Соблюдать; не размещать другие элементы вплотную к логотипу. Если точное значение не указано в задаче — уточнить у пользователя / дизайнера |
| Цветовые версии | Использовать официальные версии Flowwow / Flowwow Seller. На цветном фоне — белую или фиолетовую версию |
| На цветном фоне | Использовать белую или фиолетовую версию для максимального контраста |
| Что нельзя | Не растягивать, не вращать, не перекрашивать произвольно, не добавлять тень, обводку или эффекты |

Если работаешь без файла лого — оставь текстовый placeholder `Flowwow` в `font-family: var(--ff-font-display)` цвета `--ff-color-deep-purpur`.

---

## 2. Цветовая палитра

### 2.1 Основной цвет — Coral
Коралловый — фирменный акцент. Используется **как акцент или крупный цветовой блок**, но не как цвет body-текста.

| Токен | HEX | RGB | Назначение |
|---|---|---|---|
| `--ff-color-coral` | `#FF7663` | `255, 118, 99` | Акценты, крупные цветовые блоки |
| `--ff-color-coral-shade-4` | `#FF9486` | `255, 148, 134` | Hover / светлее основного |
| `--ff-color-coral-shade-3` | `#FFAFA4` | `255, 175, 164` | Декоративные плашки |
| `--ff-color-coral-shade-2` | `#FFC9C2` | `255, 201, 194` | Бейджи, декоративные плашки |
| `--ff-color-coral-shade-1` | `#FEE2DF` | `254, 226, 223` | Светлые секции |

### 2.2 Тёмный «фирменный»
| Токен | HEX | RGB | Назначение |
|---|---|---|---|
| `--ff-color-deep-purpur` | `#370B27` | `55, 11, 39` | Текст, логотип, тёмные секции, footer, primary CTA |

> Это **не чёрный**. Всегда используй `#370B27` вместо `#000` / `#000000` для текста и тёмных поверхностей — это даёт фирменную «тёплую» темноту.

### 2.3 Дополнительные пастельные фоны
Светлые оттенки для зонирования секций и фоновых композиций. Выбирай 1–2 оттенка на лендинг, не смешивай всю палитру в одном макете.

| Токен | HEX | RGB | Настроение |
|---|---|---|---|
| `--ff-color-soft-pink` | `#FFE9EE` | `255, 233, 238` | Розовый софт, романтика, цветы |
| `--ff-color-comfy-beige` | `#FFF1E5` | `255, 241, 229` | Тёплый, уютный |
| `--ff-color-soft-purple` | `#F1ECFF` | `241, 236, 255` | Прохладный, технологичный |
| `--ff-color-spring-blue` | `#DFEFFF` | `223, 239, 255` | Свежий, лёгкий |

### 2.4 Утилитарные токены
| Токен | HEX | Назначение |
|---|---|---|
| `--ff-color-bg` | `#FFFFFF` | Основной фон страницы |
| `--ff-color-surface` | `#F9F8F9` | Фон карточек и secondary-кнопок |
| `--ff-color-text` | `#370B27` | Основной текст |
| `--ff-color-text-muted` | `#7A5A6E` | Приглушённый текст, если не указано иначе |
| `--ff-color-border` | `#D4C9D0` | Мягкая граница input / ghost-элементов |
| `--ff-color-error` | `#D14343` | Ошибка в формах, если точный красный не указан в задаче |

### 2.5 Правила применения
- **Primary CTA**: фон `--ff-color-deep-purpur`, текст белый. На экране допустим только один доминантный CTA-цвет.
- **Secondary CTA**: фон `--ff-color-surface` (`#F9F8F9`), текст `--ff-color-deep-purpur`.
- **Deep Purpur** — фирменный тёмный neutral и primary CTA, **не заменяй его на чёрный**.
- **Coral** не используется как цвет body-текста: на белом фоне контраст недостаточен для мелкого текста.
- **На коралловом или тёмном фоне** основной текст — белый (`#FFFFFF`).
- **Зонирование секций**: чередуй белый и 1–2 пастельных фона. Не лепи все 4 пастельных фона подряд.
- **Mini Don'ts** (типовые ошибки, на которых ломается «фирменность»):
  - ❌ `color: #000` → ✅ `color: var(--ff-color-deep-purpur)`.
  - ❌ Primary-кнопка коралловая → ✅ `background: var(--ff-color-deep-purpur)`.
  - ❌ Secondary-кнопка тёмная → ✅ `background: var(--ff-color-surface)`.
  - ❌ Карточки на старом off-white surface → ✅ `background: #F9F8F9`.
  - ❌ Тени на карточках / кнопках / изображениях → ✅ без теней.
  - ❌ Body-текст коралловым → ✅ коралл только в акцентах и крупных цветовых блоках.

### 2.6 CSS-переменные одним блоком
```css
:root {
  /* Coral */
  --ff-color-coral:         #FF7663;
  --ff-color-coral-shade-4: #FF9486;
  --ff-color-coral-shade-3: #FFAFA4;
  --ff-color-coral-shade-2: #FFC9C2;
  --ff-color-coral-shade-1: #FEE2DF;

  /* Brand dark */
  --ff-color-deep-purpur:   #370B27;

  /* Pastel surfaces */
  --ff-color-soft-pink:     #FFE9EE;
  --ff-color-comfy-beige:   #FFF1E5;
  --ff-color-soft-purple:   #F1ECFF;
  --ff-color-spring-blue:   #DFEFFF;

  /* Utility */
  --ff-color-bg:            #FFFFFF;
  --ff-color-surface:       #F9F8F9;
  --ff-color-text:          var(--ff-color-deep-purpur);
  --ff-color-text-muted:    #7A5A6E;
  --ff-color-border:        #D4C9D0;
  --ff-color-error:         #D14343;
}
```

### 2.7 Те же токены для Tailwind / CSS-in-JS

Если пилотник на React + Tailwind (v3) — добавь в `tailwind.config.js`:

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        ff: {
          coral:        { DEFAULT: '#FF7663', 4: '#FF9486', 3: '#FFAFA4', 2: '#FFC9C2', 1: '#FEE2DF' },
          'deep-purpur':'#370B27',
          'soft-pink':  '#FFE9EE',
          'comfy-beige':'#FFF1E5',
          'soft-purple':'#F1ECFF',
          'spring-blue':'#DFEFFF',
          surface:      '#F9F8F9',
          'text-muted': '#7A5A6E',
          border:       '#D4C9D0',
          error:        '#D14343',
        },
      },
      fontFamily: {
        'ff-display': ['Flowfont', 'Manrope', 'system-ui', 'sans-serif'],
        'ff-text':    ['"COFO Sans Pro"', 'Manrope', 'Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: { 'ff-pill': '100px', 'ff-card': '40px', 'ff-block': '40px' },
    },
  },
};
```

Для Tailwind v4 (`@theme`) — те же значения через CSS-переменные в директиве `@theme { --color-ff-coral: #FF7663; ... }`. Для styled-components / Emotion — экспортируй объект `tokens` из единого модуля и не дублируй HEX по компонентам.

---

## 3. Типографика

### 3.1 Гарнитуры

| Роль | Шрифт | Fallback | Применение |
|---|---|---|---|
| **Display / крупные заголовки** | **Flowfont** | Manrope | Только h1/h2 и редко h3 |
| **Text / UI** | **COFO Sans Pro** | Manrope | Body, кнопки, формы, навигация, карточки |

Fallback Manrope применяется в Продуктовой песочнице, где фирменные шрифты недоступны по лицензии.

### 3.2 Фолбэки (шрифты проприетарные)
Flowfont и COFO Sans Pro — проприетарные шрифты Flowwow, в Google Fonts их нет, **в `vibecoder` template они не распространяются и от платформы их получить нельзя**. Не пытайся попросить у админа / в `канал «Песочница»` — это всё равно не сработает.

**Дефолтная стратегия для пилотника — Manrope** (есть в Google Fonts, близок по геометрии и к Flowfont, и к COFO Sans Pro). Используй Manrope и для дисплея, и для основного текста. Никаких TODO «дождаться файлов» в коде не оставляй — это и есть финальный стек.

```css
--ff-font-display: "Flowfont", "Manrope", system-ui, sans-serif;
--ff-font-text:    "COFO Sans Pro", "Manrope", "Inter", system-ui, -apple-system, sans-serif;
```

Подключение Manrope через Google Fonts:

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link rel="stylesheet"
      href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;700;800&display=swap" />
```

В этой раскладке: Manrope 400 = COFO Book, Manrope 500 = COFO Medium, Manrope 700 = COFO Bold, Manrope 800 ≈ COFO Black.

### 3.3 Иерархия
Дизайнер задал точную шкалу для лендингов. Не заменяй её clamp-рекомендациями, если в задаче не указана адаптивная шкала.

| Токен | Семейство | Начертание | Размер | Применение |
|---|---|---|---|---|
| `--ff-text-h1-fw-xl` | Flowfont | Regular / Italic | `100px` | Короткий акцидентный заголовок Hero |
| `--ff-text-h1-fw` | Flowfont | Regular / Italic | `80px` | Акцидентный заголовок Hero |
| `--ff-text-h1` | COFO Sans Pro | Regular / Italic | `80px` | Заголовок Hero без Flowfont |
| `--ff-text-h2` | COFO Sans Pro | Regular / Italic | `48px` | Заголовок блока |
| `--ff-text-h3` | COFO Sans Pro | Regular / Italic | `36px` | Подзаголовок блока, вопрос в FAQ |
| `--ff-text-h4` | COFO Sans Pro | Medium | `28px` | Заголовок карточки |
| `--ff-text-h5` | COFO Sans Pro | Medium | `24px` | Заголовок элемента внутри карточки |
| `--ff-text-h6` | COFO Sans Pro | Medium | `20px` | Заголовок внутри текста |
| `--ff-text-md` | COFO Sans Pro | Book | `16px` | Основной текст |
| `--ff-text-xs` | COFO Sans Pro | Book | `14px` | Сноска, placeholder, Open Graph |
| `--ff-text-nav` | COFO Sans Pro | Book | `16px` | Пункты меню навигации |

```css
:root {
  --ff-text-h1-fw-xl: 100px;
  --ff-text-h1-fw:    80px;
  --ff-text-h1:       80px;
  --ff-text-h2:       48px;
  --ff-text-h3:       36px;
  --ff-text-h4:       28px;
  --ff-text-h5:       24px;
  --ff-text-h6:       20px;
  --ff-text-md:       16px;
  --ff-text-xs:       14px;
  --ff-text-nav:      16px;
}
```

### 3.4 Letter-spacing и Line-height
| Стиль | Letter-spacing | Line-height |
|---|---|---|
| Flowfont (`h1 fw xl`, `h1 fw`) | `0` | `100–110%` |
| COFO Sans Pro — заголовки (`h1–h3`) | `0` | `110–120%` |
| COFO Sans Pro — карточки (`h4–h6`) | `0` | `120–130%` |
| COFO Sans — body, nav-link, text xs | `0.03em` по брендбуку; допускается `0.01em`, если текст визуально слишком разрежен | `150%` |

### 3.5 Базовые стили
```css
*, *::before, *::after { box-sizing: border-box; }

html { font-size: 16px; }

body {
  font-family: var(--ff-font-text);
  font-weight: 400;            /* COFO Sans Pro Book */
  font-size: var(--ff-text-md);
  line-height: 1.5;
  letter-spacing: 0.03em;
  color: var(--ff-color-text);
  background: var(--ff-color-bg);
}

h1, h2, h3, h4, h5, h6,
.ff-display {
  margin: 0;
  color: var(--ff-color-text);
  text-wrap: balance;
}

.ff-h1-fw-xl,
.ff-h1-fw,
.ff-display {
  font-family: var(--ff-font-display);
  font-weight: 400;
  line-height: 1.05;
  letter-spacing: 0;
}

h1, h2, h3 {
  font-family: var(--ff-font-text);
  font-weight: 400;
  line-height: 1.15;
  letter-spacing: 0;
}

h4, h5, h6 {
  font-family: var(--ff-font-text);
  font-weight: 500;
  line-height: 1.25;
  letter-spacing: 0;
}

.ff-h1-fw-xl { font-size: var(--ff-text-h1-fw-xl); }
.ff-h1-fw { font-size: var(--ff-text-h1-fw); }
h1 { font-size: var(--ff-text-h1); }
h2 { font-size: var(--ff-text-h2); }
h3 { font-size: var(--ff-text-h3); }
h4 { font-size: var(--ff-text-h4); }
h5 { font-size: var(--ff-text-h5); }
h6 { font-size: var(--ff-text-h6); }

strong, b { font-weight: 700; }
.ff-black { font-weight: 800; }
```

### 3.6 Правила применения
- Flowfont — только для акцидентных h1/h2 и редко h3. Для кнопок и UI — основной шрифт.
- Если Flowfont недоступен, используй Manrope и не оставляй TODO в коде.
- На коралловом или тёмном фоне используй белый цвет, на пастельных — `deep-purpur`.
- Если размер заголовка не помещается на mobile, адаптацию уточни у пользователя / дизайнера или задай локальный mobile-size без изменения desktop-токена.

---

## 4. Сетка и отступы

### 4.1 Сетка (desktop 1440px)
Дизайнер задал сетку для базового разрешения `1440px`.

| Параметр | Значение |
|---|---|
| Разрешение (базовое) | `1440px` |
| Количество колонок | `6` |
| Боковые отступы (margin) | `100px` |
| Gutter | `20px` |
| Ширина контента (между полями) | `1240px` |

```css
:root {
  --ff-container-max: 1440px;          /* внешняя ширина: 1240px контента + 2×100px поля */
  --ff-container-pad-desktop: 100px;
  --ff-grid-columns: 6;
  --ff-grid-gutter: 20px;
}

.ff-container {
  max-width: var(--ff-container-max);
  margin-inline: auto;
  padding-inline: var(--ff-container-pad-desktop);   /* боковые поля 100px → контент 1240px */
}

.ff-grid {
  display: grid;
  grid-template-columns: repeat(var(--ff-grid-columns), minmax(0, 1fr));
  gap: var(--ff-grid-gutter);
}

@media (max-width: 767px) {
  .ff-container {
    padding-inline: 16px;
  }
}
```

### 4.2 Отступы между секциями
| Брейкпоинт | Значение |
|---|---|
| Desktop | `200px` |
| Mobile | `100px` |

```css
:root {
  --ff-section-gap-desktop: 200px;   /* целевой зазор МЕЖДУ соседними секциями */
  --ff-section-gap-mobile: 100px;
}

.ff-section {
  padding-block: calc(var(--ff-section-gap-desktop) / 2);   /* 100px на сторону → 200px между секциями */
}

@media (max-width: 767px) {
  .ff-section {
    padding-block: calc(var(--ff-section-gap-mobile) / 2);  /* 50px на сторону → 100px между секциями */
  }
}
```

### 4.3 Отступы в блоках с карточками
| Параметр | Desktop | Mobile |
|---|---|---|
| Gap между карточками | `20px` | `12px` |

```css
.ff-card-grid {
  display: grid;
  gap: 20px;
}

@media (max-width: 767px) {
  .ff-card-grid { gap: 12px; }
}
```

### 4.4 Отступы внутри карточки
| Параметр | Значение |
|---|---|
| Внутренний padding карточки | `24px` |
| Расстояние между элементами (группа / заголовок + подзаголовок) | `12px` |
| Расстояние между смежными элементами | `8px` |
| Минимальный отступ (иконка / метка / бейдж) | `4px` |

```css
:root {
  --ff-card-pad: 24px;
  --ff-gap-group: 12px;
  --ff-gap-adjacent: 8px;
  --ff-gap-min: 4px;
}
```

### 4.5 Радиусы
| Элемент | Radius |
|---|---|
| Кнопки | pill (`border-radius: 100px`) |
| Карточки | `40px` |
| Крупные блоки и изображения | `40px` |
| Input | pill (`border-radius: 100px`) |

```css
:root {
  --ff-radius-pill: 100px;
  --ff-radius-card: 40px;
  --ff-radius-block: 40px;
}
```

### 4.6 Тени
Тени **не используются ни на каких элементах**: ни кнопки, ни карточки, ни изображения, ни крупные блоки.

```css
:root {
  --ff-shadow-none: none;
}

.ff-card,
.ff-btn,
.ff-hero__media,
.ff-field__input {
  box-shadow: none;
}
```

**Принципы**
- Сетка на desktop: `6` колонок, контент `1240px` (контейнер `1440px`), `20px` gutter.
- Между секциями — `200px` на desktop и `100px` на mobile.
- Карточки, крупные блоки и изображения — radius `40px`.
- Тени отсутствуют полностью.

---

## 5. Декоративная графика

Брендбук выделяет несколько типов графики. ИИ-агенту: **не пытайся генерировать фирменные иллюстрации SVG вручную** — это сложные иллюстрации. Вместо этого ставь placeholder’ы и проси у пользователя ассеты.

### 5.1 2D-графика / иллюстрации
Используется по брендбуку и Figma UI-kit. Не генерируй логотипные образы самостоятельно.

### 5.2 3D-графика
Используй официальную библиотеку 3D-ассетов по названию и категории. Если ассет недоступен — ставь технический placeholder.

### 5.3 Генеративные изображения
Допустимы только в фотореалистичном стиле, без холодных синих оттенков, в продуктовой стилистике. Если точный стиль не указан в задаче — уточнить у пользователя / дизайнера.

### 5.4 Иконки
Иконки брать из дизайн-системы; стиль и толщина линий должны быть едиными по UI-kit. Если иконка недоступна — используй placeholder и не смешивай разные стили.

### Placeholder в коде
```html
<figure class="ff-illustration-placeholder"
        style="aspect-ratio:1/1; background:var(--ff-color-surface);
               border-radius:var(--ff-radius-block); display:grid; place-items:center;
               box-shadow:none; font-family:monospace; font-size:14px;
               color:var(--ff-color-deep-purpur);">
  <!-- DROP: официальный 3D-ассет / продуктовое фото / фотореалистичное изображение -->
  drop: official asset placeholder
</figure>
```

---

## 6. UI-компоненты

Сниппеты ниже — базовые компоненты для лендингов в Песочнице. Не меняй значения из токенов, если задача не требует отдельного сценария.

### 6.1 Кнопки

```html
<!-- Primary -->
<button class="ff-btn ff-btn--primary">Оформить заказ</button>

<!-- Secondary -->
<button class="ff-btn ff-btn--secondary">Узнать подробнее</button>
```

```css
.ff-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 52px;
  padding: 16px 28px;
  border: 1px solid transparent;
  border-radius: var(--ff-radius-pill);
  box-shadow: none;
  font-family: var(--ff-font-text);
  font-size: 16px;
  font-weight: 500;
  line-height: 1;
  letter-spacing: 0.03em;
  cursor: pointer;
  transition: background .15s ease, color .15s ease, border-color .15s ease;
}

.ff-btn--primary {
  background: var(--ff-color-deep-purpur);
  color: #fff;
}

.ff-btn--secondary {
  background: var(--ff-color-surface);
  color: var(--ff-color-deep-purpur);
}

.ff-btn:disabled {
  opacity: .4;
  cursor: not-allowed;
}

.ff-btn:focus-visible {
  outline: 2px solid var(--ff-color-coral);
  outline-offset: 3px;
}
```

Если hover-состояние для primary / secondary не указано в задаче — уточни у пользователя / дизайнера или используй состояние из UI-kit. Не добавляй универсальный opacity-hover для всех кнопок.

### 6.2 Карточка (фича / продукт)

```html
<article class="ff-card">
  <div class="ff-card__media">
    <!-- DROP: иллюстрация / фото продукта -->
  </div>
  <h4 class="ff-card__title">Доставка от 30 минут</h4>
  <p class="ff-card__text">
    Оформите заказ и выберите доставку ко времени или как можно скорее.
  </p>
</article>
```

```css
.ff-card {
  display: flex;
  flex-direction: column;
  gap: var(--ff-gap-group);
  padding: var(--ff-card-pad);
  background: var(--ff-color-surface);
  border-radius: var(--ff-radius-card);
  border: 0;
  box-shadow: none;
}

.ff-card__media {
  aspect-ratio: 4 / 3;
  background: #fff;
  border-radius: var(--ff-radius-block);
  box-shadow: none;
}

.ff-card__title {
  font-family: var(--ff-font-text);
  font-size: var(--ff-text-h4);
  font-weight: 500;
  line-height: 1.25;
  letter-spacing: 0;
  margin: 0;
}

.ff-card__text {
  margin: 0;
  color: var(--ff-color-text);
  font-size: var(--ff-text-md);
  line-height: 1.5;
}
```

### 6.3 Input / форма

```html
<form class="ff-form">
  <label class="ff-field">
    <span class="ff-field__label">Email</span>
    <input class="ff-field__input" type="email" placeholder="you@company.com" />
    <span class="ff-field__helper">Helper-текст или ошибка</span>
  </label>
  <button class="ff-btn ff-btn--primary" type="submit">Получить доступ</button>
</form>
```

```css
.ff-form { display: grid; gap: 20px; }

.ff-field { display: grid; gap: 8px; }
.ff-field__label {
  font-size: var(--ff-text-xs);
  line-height: 1.5;
  letter-spacing: 0.03em;
  color: var(--ff-color-text);
}

.ff-field__input {
  height: 52px;
  padding: 0 18px;
  border-radius: var(--ff-radius-pill);
  border: 1px solid var(--ff-color-border);
  background: #fff;
  box-shadow: none;
  font: inherit;
  color: var(--ff-color-text);
  transition: border-color .15s ease, opacity .15s ease;
}

.ff-field__input::placeholder {
  color: var(--ff-color-text-muted);
  font-size: var(--ff-text-xs);
}

.ff-field__input:focus {
  border-color: var(--ff-color-coral);
}

.ff-field__input:focus-visible {
  outline: 2px solid var(--ff-color-coral);
  outline-offset: 2px;
}

.ff-field__input:disabled {
  opacity: .4;
  cursor: not-allowed;
}

.ff-field--error .ff-field__input {
  border-color: var(--ff-color-error);
}

.ff-field__helper {
  font-size: var(--ff-text-xs);
  line-height: 1.5;
}

.ff-field--error .ff-field__helper {
  color: var(--ff-color-error);
}
```

### 6.4 Badge / pill (категории, метки)

```html
<span class="ff-badge ff-badge--pink">Хит</span>
<span class="ff-badge ff-badge--purple">B2B</span>
```

```css
.ff-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--ff-gap-min);
  padding: 6px 14px;
  border-radius: var(--ff-radius-pill);
  font-size: var(--ff-text-xs);
  font-weight: 500;
  letter-spacing: 0.03em;
  line-height: 1.5;
  color: var(--ff-color-deep-purpur);
  box-shadow: none;
}

.ff-badge--pink   { background: var(--ff-color-soft-pink); }
.ff-badge--purple { background: var(--ff-color-soft-purple); }
.ff-badge--blue   { background: var(--ff-color-spring-blue); }
.ff-badge--beige  { background: var(--ff-color-comfy-beige); }
.ff-badge--coral  { background: var(--ff-color-coral-shade-2); }
```

### 6.5 Hero-блок (типовая структура)

```html
<section class="ff-section ff-hero" style="background: var(--ff-color-soft-pink);">
  <div class="ff-container ff-hero__grid">
    <div class="ff-hero__copy">
      <span class="ff-badge ff-badge--pink">Для бизнеса</span>
      <h1 class="ff-h1-fw">Откройте магазин на Флаувау</h1>
      <p class="ff-hero__lead">
        Управляйте магазином и заказами прямо с телефона.
      </p>
      <div class="ff-hero__cta">
        <a class="ff-btn ff-btn--primary" href="#start">Открыть магазин</a>
        <a class="ff-btn ff-btn--secondary" href="#more">Как это работает</a>
      </div>
    </div>
    <div class="ff-hero__media">
      <!-- DROP: официальный 3D-коллаж или продуктовое фото -->
    </div>
  </div>
</section>
```

```css
.ff-hero__grid {
  display: grid;
  gap: 20px;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  align-items: center;
}

.ff-hero__copy {
  grid-column: span 3;
  display: grid;
  gap: var(--ff-gap-group);
}

.ff-hero__lead {
  font-size: var(--ff-text-md);
  line-height: 1.5;
  color: var(--ff-color-text);
  max-width: 52ch;
  margin: 0;
}

.ff-hero__cta {
  display: flex;
  gap: var(--ff-gap-group);
  flex-wrap: wrap;
}

.ff-hero__media {
  grid-column: span 3;
  aspect-ratio: 1 / 1;
  background: var(--ff-color-surface);
  border-radius: var(--ff-radius-block);
  box-shadow: none;
}

@media (max-width: 899px) {
  .ff-hero__grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .ff-hero__copy,
  .ff-hero__media {
    grid-column: auto;
  }
}

@media (max-width: 767px) {
  /* Акцидентный hero-заголовок не помещается на 320px при фикс. desktop-размере
     (§3.6): локальный mobile-size для примера, desktop-токен не трогаем.
     Точный размер — зона дизайнера (§9), это разумный дефолт. */
  .ff-hero__copy .ff-h1-fw {
    font-size: clamp(36px, 9vw, var(--ff-text-h1-fw));
  }
}
```

### 6.6 Footer (минимальный)

```html
<footer class="ff-footer">
  <div class="ff-container ff-footer__grid">
    <!-- Placeholder до появления официального белого логотипа Flowwow / Flowwow Seller -->
    <span class="ff-footer__logo">Flowwow</span>
    <nav class="ff-footer__nav">
      <a href="#">Покупателям</a>
      <a href="#">Продавцам</a>
      <a href="#">Доставка</a>
      <a href="#">Контакты</a>
    </nav>
    <small class="ff-footer__legal">© Flowwow, 2026</small>
  </div>
</footer>

<style>
.ff-footer {
  background: var(--ff-color-deep-purpur);
  color: #fff;
  padding-block: 64px;
  box-shadow: none;
}

.ff-footer__grid {
  display: grid;
  gap: 32px;
}

.ff-footer__logo {
  font-family: var(--ff-font-display);
  font-size: 24px;
  line-height: 1;
  letter-spacing: 0;
  color: #fff;
}

.ff-footer__nav {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
}

.ff-footer__nav a {
  color: #fff;
  text-decoration: none;
  opacity: .85;
}

.ff-footer__nav a:hover { opacity: 1; }
.ff-footer__legal { opacity: .6; }
</style>
```

---

## 7. Чек-лист для агента перед сдачей лендинга

Проходит **до** L2 (демонстрации оунеру на локальном preview — см. `./dev-workflow.md` §2.6: `make preview` только для статичной заглушки, иначе команда стека).

- [ ] Подключены CSS-переменные из разделов 2–4 в `:root`.
- [ ] `*, *::before, *::after { box-sizing: border-box; }` включён.
- [ ] Текст по умолчанию — `--ff-color-deep-purpur`, **не** `#000` / `#000000`.
- [ ] Primary CTA — Deep Purpur фон, белый текст, `border-radius: pill`; на экране один доминантный CTA.
- [ ] Secondary CTA — фон `#F9F8F9`, текст Deep Purpur.
- [ ] Coral не используется как body-текст; на коралловом или тёмном фоне основной текст белый.
- [ ] Карточки и secondary-фоны используют `#F9F8F9`.
- [ ] Desktop-сетка: 6 колонок, контент `1240px` (контейнер `1440px` − 2×`100px` поля), `20px` gutter.
- [ ] Между секциями: `200px` на desktop и `100px` на mobile.
- [ ] Gap между карточками: `20px` desktop и `12px` mobile.
- [ ] Padding карточки `24px`; внутренние расстояния: `12px`, `8px`, минимум `4px`.
- [ ] Радиусы: кнопки и input pill / `100px`, карточки, крупные блоки и изображения `40px`.
- [ ] Теней нет ни на одном элементе: кнопки, карточки, изображения, блоки.
- [ ] Заголовки и body используют размеры, line-height и letter-spacing из раздела 3.
- [ ] Hero использует h1 / h1 fw / h1 fw xl, один primary CTA и placeholder под 3D-коллаж или продуктовое фото.
- [ ] Иллюстрации, 3D и иконки берутся из официальных ресурсов; если ассетов нет — стоит технический placeholder.
- [ ] Генеративные изображения, если нужны, фотореалистичные, без холодных синих оттенков.
- [ ] Логотип высотой `30px`, не растянут, не повёрнут, не перекрашен произвольно, без тени и обводки.
- [ ] Интерактивные элементы имеют `:focus-visible` стиль; input содержит focus, disabled, error и placeholder-состояния.
- [ ] Поднял лендинг в локальном preview (`make preview` — только для статичной заглушки, иначе команда стека; см. `./dev-workflow.md` §2.6) и проверил на 320 px (mobile) и 1440 px (desktop): hero не ломается, CTA остаётся видимым, текст не наезжает.

---

## 8. Ограничения и запреты

- Тёмной темы нет — все лендинги только светлые.
- Тени отсутствуют на всех элементах: ни кнопки, ни карточки, ни изображения.
- Coral (`#FF7663`) не используется как цвет body-текста.
- Deep Purpur (`#370B27`) не заменяется на `#000000`.
- Логотип нельзя растягивать, вращать, перекрашивать произвольно, добавлять тень или обводку.
- Не смешивать все пастельные фоны в одном лендинге — выбрать 1–2 оттенка.
- На экране допустим только один доминантный CTA-цвет: Deep Purpur для primary.
- ИИ-агент не рисует фирменные иллюстрации самостоятельно — только ставит placeholder.
- Генеративные изображения — только фотореалистичный стиль, без холодных синих оттенков.

---

## 9. Что **не** указано в брендбуке (зоны риска)

Если на эти темы прилетает задача — спроси у пользователя / дизайнера или ставь явную пометку, не выдумывай:

- Точные mobile-размеры типографики для всех заголовков.
- Breakpoints, кроме указанной проверки mobile и desktop.
- Hover-состояния primary / secondary CTA, если они не указаны в задаче или UI-kit.
- Точный красный для error-состояния, если нужен брендовый error-token.
- Анимации и motion-принципы.
- Стили графиков, таблиц, инфографики.
- Любые ассеты, которых нет в Figma / официальной библиотеке.
