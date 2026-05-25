# Дизайн-система для ИИ-агентов

> Файл-памятка для LLM-агентов (Claude, GPT и др.), которые верстают HTML/CSS-лендинги в "Песочнице".
> Фокус: продуктовые / B2B-лендинги (фичи, для бизнеса, для продавцов).

---

## 1. Логотип

### Доступные варианты
- Основной логотип Flowwow (полноцветный, монохром, белый, фиолетовый).
- Логотип Flowwow Seller (для B2B-материалов).

### Правила использования
| Правило | Значение |
|---|---|
| Минимальные охранные поля | `// не указано в брендбуке` — используй ≥ 0.5× высоты лого со всех сторон |
| Минимальный размер | `// не указано в брендбуке` — рекомендую ≥ 24 px по высоте на экране |
| Цветовые версии | Фиолетовый (`#370B27` — Deep Purpur), коралловый (`#FF7663`), белый, чёрный |
| На цветном фоне | Использовать белую или фиолетовую версию для максимального контраста |
| Что нельзя | `// не указано в брендбуке` — стандартно: не вращать, не растягивать, не менять цвета, не добавлять обводку/тень |

Если работаешь без файла лого — оставь текстовый placeholder `Flowwow` в `font-family: var(--ff-font-display)` цвета `--ff-color-deep-purpur`.

---

## 2. Цветовая палитра

### 2.1 Основной цвет — Coral
Коралловый — главный фирменный цвет. Используется **как фон или как акцент** (CTA, выделение, фоновые блоки).

| Токен | HEX | RGB | Назначение |
|---|---|---|---|
| `--ff-color-coral` | `#FF7663` | `255, 118, 99` | Основной коралловый, CTA / фон / акцент |
| `--ff-color-coral-shade-4` | `#FF9486` | `255, 148, 134` | Hover / светлее основного |
| `--ff-color-coral-shade-3` | `#FFAFA4` | `255, 175, 164` | Декоративные плашки |
| `--ff-color-coral-shade-2` | `#FFC9C2` | `255, 201, 194` | Светлый фон, badges |
| `--ff-color-coral-shade-1` | `#FEE2DF` | `254, 226, 223` | Очень светлый фон секций |

### 2.2 Тёмный «фирменный»
| Токен | HEX | RGB | Назначение |
|---|---|---|---|
| `--ff-color-deep-purpur` | `#370B27` | `55, 11, 39` | Основной цвет текста, логотип, тёмные секции, footer |

> Это **не чёрный**. Всегда используй `#370B27` вместо `#000` для текста и тёмных поверхностей — это даёт фирменную «тёплую» темноту.

### 2.3 Дополнительные пастельные фоны
Светлые оттенки для зонирования секций и фоновых композиций.

| Токен | HEX | RGB | Настроение |
|---|---|---|---|
| `--ff-color-soft-pink` | `#FFE9EE` | `255, 233, 238` | Розовый софт, романтика, цветы |
| `--ff-color-comfy-beige` | `#FFF1E5` | `255, 241, 229` | Тёплый, уютный |
| `--ff-color-soft-purple` | `#F1ECFF` | `241, 236, 255` | Прохладный, технологичный |
| `--ff-color-spring-blue` | `#DFEFFF` | `223, 239, 255` | Свежий, лёгкий |

### 2.4 Утилитарные (производные) `// не указано в брендбуке`
Для интерфейсной работы добавь нейтральные токены, выдержанные в тёплой гамме бренда:

```css
--ff-color-bg:        #FFFFFF;
--ff-color-surface:   #FFFAF7;   /* тёплый off-white */
--ff-color-text:      #370B27;   /* deep purpur */
--ff-color-text-muted:#7A5A6E;   /* приглушённый */
--ff-color-border:    #EFE4DD;   /* мягкая граница */
--ff-color-success:   #2E8B57;   /* нейтральный, бренд не задаёт */
--ff-color-warning:   #C97A1A;
--ff-color-error:     #D14343;
```

### 2.5 Правила применения
- **Один доминантный акцент на экране** — коралл. `deep-purpur` — это **neutral / dark surface** (текст, тёмные секции, footer), **не второй акцент**. Не миксуй коралл и deep-purpur как два равноправных CTA-цвета.
- **Текст**: `--ff-color-deep-purpur` на светлом, белый на коралловом / тёмном.
- **CTA**: фон `--ff-color-coral`, текст белый. Hover — `--ff-color-coral-shade-4`.
- **Зонирование секций**: чередуй белый → `comfy-beige` → `soft-pink` / `spring-blue` / `soft-purple`. Не лепи все 4 пастельных фона подряд — выбирай 1–2 на лендинг.
- **Контраст coral на белом**: `#FF7663` на `#FFFFFF` даёт contrast ratio ≈ 3.0:1. По WCAG AA это проходит **только для large text** (≥24 px regular или ≥18.7 px bold). Для body, UI-надписей, secondary-текста — **всегда** `deep-purpur` или белый, не коралл.
- **Mini Don'ts** (типовые ошибки, на которых ломается «фирменность»):
  - ❌ `color: #000` → ✅ `color: var(--ff-color-deep-purpur)` (даже когда кажется «всё равно чёрный»).
  - ❌ Кнопка `border-radius: 4px` → ✅ `var(--ff-radius-pill)`.
  - ❌ Два равных CTA-цвета (коралл + deep-purpur одинакового веса) → ✅ один коралловый CTA, остальное — neutral.
  - ❌ Body-текст коралловым → ✅ коралл только в крупных display-заголовках или decorative-элементах.

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

  /* Derived utility (// не указано в брендбуке) */
  --ff-color-bg:            #FFFFFF;
  --ff-color-surface:       #FFFAF7;
  --ff-color-text:          var(--ff-color-deep-purpur);
  --ff-color-text-muted:    #7A5A6E;
  --ff-color-border:        #EFE4DD;
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
          surface:      '#FFFAF7',
          'text-muted': '#7A5A6E',
          border:       '#EFE4DD',
        },
      },
      fontFamily: {
        'ff-display': ['Flowfont', 'Unbounded', 'Manrope', 'system-ui', 'sans-serif'],
        'ff-text':    ['"COFO Sans Pro"', 'Manrope', 'Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: { 'ff-pill': '999px', 'ff-lg': '24px', 'ff-xl': '32px' },
    },
  },
};
```

Для Tailwind v4 (`@theme`) — те же значения через CSS-переменные в директиве `@theme { --color-ff-coral: #FF7663; ... }`. Для styled-components / Emotion — экспортируй объект `tokens` из единого модуля и не дублируй HEX по компонентам.

---

## 3. Типографика

### 3.1 Гарнитуры

| Роль | Шрифт | Начертания | Letter spacing | Line height |
|---|---|---|---|---|
| **Дисплейный** (акцентные заголовки) | **Flowfont** | Regular | `0%` | `100–110%` |
| **Основной** (тексты, UI) | **COFO Sans Pro** | Book, Medium, Bold, Black | `3%` | `100–110%` |

> **Важно про letter-spacing**: для COFO Sans Pro брендбук задаёт **трекинг 3%** — это `letter-spacing: 0.03em`. Не забывай, иначе текст будет «не наш».

### 3.2 Фолбэки (шрифты проприетарные)
Flowfont и COFO Sans Pro — проприетарные шрифты Flowwow, в Google Fonts их нет, **в `vibecoder` template они не распространяются и от платформы их получить нельзя**. Не пытайся попросить у админа / в `канал «Песочница / поддержка и новости»` — это всё равно не сработает.

**Дефолтная стратегия для пилотника — Manrope** (есть в Google Fonts, близок по геометрии и к Flowfont, и к COFO Sans Pro). Используй Manrope и для дисплея, и для основного текста. Никаких TODO «дождаться файлов» в коде не оставляй — это и есть финальный стек.

```css
/* Дисплейный (Flowfont/Unbounded оставлены в стеке на случай, если у проекта */
/* появится своя лицензия и @font-face — браузер автоматически приоритизирует) */
--ff-font-display: "Flowfont", "Unbounded", "Manrope", system-ui, sans-serif;

/* Основной */
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

### 3.3 Иерархия `// не указано в брендбуке`
Брендбук фиксирует только гарнитуры, начертания, line-height и letter-spacing. Шкалу размеров я даю как рекомендацию, выровненную под типичный лендинг:

```css
:root {
  /* Display */
  --ff-text-display-1: clamp(48px, 7vw, 96px);   /* hero h1 */
  --ff-text-display-2: clamp(36px, 5vw, 64px);   /* section h2 */
  --ff-text-display-3: clamp(28px, 3.5vw, 44px); /* subsection */

  /* Body */
  --ff-text-xl: 22px;   /* lead / подзаголовок hero */
  --ff-text-lg: 18px;   /* акцентный параграф */
  --ff-text-md: 16px;   /* основной текст */
  --ff-text-sm: 14px;   /* подписи, метаданные */
  --ff-text-xs: 12px;   /* legal / footer */
}
```

### 3.4 Базовые стили
```css
*, *::before, *::after { box-sizing: border-box; }

html { font-size: 16px; }

body {
  font-family: var(--ff-font-text);
  font-weight: 400;            /* COFO Sans Pro Book */
  font-size: var(--ff-text-md);
  line-height: 1.05;           /* 100–110% */
  letter-spacing: 0.03em;      /* 3% — см. caveat ниже */
  color: var(--ff-color-text);
  background: var(--ff-color-bg);
}

h1, h2, h3,
.ff-display {
  font-family: var(--ff-font-display);
  font-weight: 400;            /* Flowfont Regular */
  line-height: 1.0;            /* плотнее, 100% */
  letter-spacing: 0;           /* 0% — у Flowfont трекинга нет */
  color: var(--ff-color-text);
  text-wrap: balance;
}

h1 { font-size: var(--ff-text-display-1); }
h2 { font-size: var(--ff-text-display-2); }
h3 { font-size: var(--ff-text-display-3); }

strong, b { font-weight: 700; }   /* COFO Bold */
.ff-black { font-weight: 900; }   /* COFO Black для редких ультра-акцентов */
```

### 3.5 Правила применения
- Дисплейный шрифт **только** для крупных заголовков (h1/h2 и редко h3). Для кнопок и UI — основной.
- Не миксуй жирные начертания дисплея и текста в одной строке — это создаёт визуальный шум.
- На коралловом фоне используй белый цвет, на пастельных — `deep-purpur`.

> **Caveat про letter-spacing 0.03em на body.** В дизайн-софте «трекинг 3%» из брендбука обычно применяется к крупным надписям / uppercase. На body-тексте 14–16 px это создаёт заметно «разреженный» вид. Если визуально текст ощущается «не как на flowwow.com» — допустимо снизить до `0.01em` на body и оставить `0.03em` только на дисплейных размерах и UI-элементах с uppercase. Это компромисс «по букве доки vs по живому ощущению»; при сомнениях — спроси оунера, какой вариант ближе.

---

## 4. Сетка и отступы `// не указано в брендбуке`

Брендбук не задаёт layout-систему. Используй стандартную для современного лендинга 12-колоночную сетку и spacing-шкалу с базой 4 px:

```css
:root {
  /* Spacing scale (4-base) */
  --ff-space-1:  4px;
  --ff-space-2:  8px;
  --ff-space-3:  12px;
  --ff-space-4:  16px;
  --ff-space-5:  24px;
  --ff-space-6:  32px;
  --ff-space-7:  48px;
  --ff-space-8:  64px;
  --ff-space-9:  96px;
  --ff-space-10: 128px;

  /* Container & layout */
  --ff-container-max: 1280px;
  --ff-container-pad: clamp(16px, 4vw, 48px);
  --ff-section-pad-y: clamp(64px, 10vw, 128px);

  /* Radii — крупные, скруглённые в духе бренда */
  --ff-radius-sm: 8px;
  --ff-radius-md: 16px;
  --ff-radius-lg: 24px;
  --ff-radius-xl: 32px;
  --ff-radius-pill: 999px;

  /* Shadow — мягкие тёплые тени */
  --ff-shadow-sm: 0 2px 8px rgba(55, 11, 39, 0.06);
  --ff-shadow-md: 0 8px 24px rgba(55, 11, 39, 0.08);
  --ff-shadow-lg: 0 24px 64px rgba(55, 11, 39, 0.12);
}

.ff-container {
  max-width: var(--ff-container-max);
  margin-inline: auto;
  padding-inline: var(--ff-container-pad);
}

.ff-section {
  padding-block: var(--ff-section-pad-y);
}
```

**Принципы**
- Большие воздушные отступы между секциями (`--ff-section-pad-y`).
- Скруглённые углы — фирменный приём, используется агрессивно (карточки, кнопки, изображения).
- Картинки в карточках — `border-radius: var(--ff-radius-lg)` минимум.

---

## 5. Декоративная графика

Брендбук выделяет **три типа графики**. ИИ-агенту: **не пытайся генерировать их SVG вручную** — это сложные иллюстрации. Вместо этого ставь placeholder’ы и проси у пользователя ассеты.

### 5.1 2D-графика (базовая)
Атрибуты «волшебного мира» Flowwow — летающие элементы, воздушные сюжеты. Дополняют типографику и продуктовые композиции.

### 5.2 2D-графика (продуктовая)
Иллюстрации более конкретных тем — цветы, букеты, подарки, торты, упаковка.

### 5.3 3D-графика
3D-объекты для точной передачи продукта и подсветки лого / его частей. Самая «премиальная» категория.

### Placeholder в коде
```html
<figure class="ff-illustration-placeholder"
        style="aspect-ratio:1/1; background:var(--ff-color-coral-shade-1);
               border-radius:var(--ff-radius-lg); display:grid; place-items:center;
               font-family:monospace; font-size:14px; color:var(--ff-color-deep-purpur);">
  <!-- DROP: 3D-иллюстрация продукта (букет / торт / коробка) -->
  drop: 3d product illustration
</figure>
```

---

## 6. Tone of voice (голос бренда) `// не указано в брендбуке`

Брендбук не содержит явной TOV-главы. Рекомендации выведены из визуальной системы (тёплая, эмоциональная, «волшебная»):

| Свойство | Как писать | Как **не** писать |
|---|---|---|
| Тон | Тёплый, дружелюбный, обращение на «ты» в B2C, на «вы» в B2B (Seller) | Сухой канцелярит, «уважаемый клиент» |
| Длина | Короткие предложения, активный залог | Длинные обороты с «является», «осуществляется» |
| Лексика | Простые слова, бытовые сравнения, эмоциональные глаголы (везём, дарим, радуем) | Маркетинговый штамп («инновационное решение», «уникальная возможность») |
| Цифры | Конкретика: «4500 продавцов», «доставка за 60 минут» | Размытые «много», «быстро» |
| Эмодзи | Сдержанно, 0–1 на блок, только релевантные (🌷🎁) | Каскад эмодзи на каждом подзаголовке |
| Восклицания | Допустимы в CTA, редко в тексте | `!!!` в каждом предложении |

### Примеры заголовков
- ✅ «Доставим букет за час»
- ✅ «Откройте магазин на Flowwow — без вложений»
- ❌ «Революционная платформа для современного e-commerce»

---

## 7. UI-компоненты `// не указано в брендбуке — производное`

Брендбук не содержит UI-кита. Сниппеты ниже — **рекомендация в духе бренда**: коралловые CTA, скруглённые формы, deep-purpur типографика. Их можно безопасно использовать на лендингах.

### 7.1 Кнопки

```html
<!-- Primary -->
<button class="ff-btn ff-btn--primary">Оформить заказ</button>

<!-- Secondary -->
<button class="ff-btn ff-btn--secondary">Узнать подробнее</button>

<!-- Ghost -->
<button class="ff-btn ff-btn--ghost">Отмена</button>
```

```css
.ff-btn {
  display: inline-flex; align-items: center; gap: 8px;
  font-family: var(--ff-font-text);
  font-weight: 500;             /* COFO Medium */
  font-size: 16px;
  line-height: 1;
  letter-spacing: 0.03em;
  padding: 16px 28px;
  border-radius: var(--ff-radius-pill);
  border: 1px solid transparent;
  cursor: pointer;
  transition: background .15s ease, color .15s ease, border-color .15s ease;
}

.ff-btn--primary {
  background: var(--ff-color-coral);
  color: #fff;
}
.ff-btn--primary:hover { background: var(--ff-color-coral-shade-4); }

.ff-btn--secondary {
  background: var(--ff-color-deep-purpur);
  color: #fff;
}
.ff-btn--secondary:hover { background: #4d1638; }

.ff-btn--ghost {
  background: transparent;
  color: var(--ff-color-deep-purpur);
  border-color: var(--ff-color-border);
}
.ff-btn--ghost:hover { background: var(--ff-color-surface); }

/* Универсальный focus-ring для всех кнопок — обязателен для a11y */
.ff-btn:focus-visible {
  outline: 2px solid var(--ff-color-coral);
  outline-offset: 3px;
}
```

### 7.2 Карточка (фича / продукт)

```html
<article class="ff-card">
  <div class="ff-card__media">
    <!-- DROP: иллюстрация / фото продукта -->
  </div>
  <h3 class="ff-card__title">Доставка за 60 минут</h3>
  <p class="ff-card__text">
    Курьер привозит букет в течение часа после оформления заказа.
  </p>
</article>
```

```css
.ff-card {
  display: flex; flex-direction: column; gap: 16px;
  padding: 24px;
  background: var(--ff-color-surface);
  border-radius: var(--ff-radius-lg);
  border: 1px solid var(--ff-color-border);
}
.ff-card__media {
  aspect-ratio: 4 / 3;
  background: var(--ff-color-coral-shade-1);
  border-radius: var(--ff-radius-md);
}
.ff-card__title {
  font-family: var(--ff-font-display);
  font-size: 24px; line-height: 1; letter-spacing: 0;
  margin: 0;
}
.ff-card__text {
  margin: 0;
  color: var(--ff-color-text-muted);
  font-size: 16px; line-height: 1.4;
}
```

### 7.3 Input / форма

```html
<form class="ff-form">
  <label class="ff-field">
    <span class="ff-field__label">Email</span>
    <input class="ff-field__input" type="email" placeholder="you@company.com" />
  </label>
  <button class="ff-btn ff-btn--primary" type="submit">Получить доступ</button>
</form>
```

```css
.ff-form { display: grid; gap: 16px; }

.ff-field { display: grid; gap: 6px; }
.ff-field__label {
  font-size: 14px; letter-spacing: 0.03em;
  color: var(--ff-color-text-muted);
}
.ff-field__input {
  height: 52px;
  padding: 0 18px;
  border-radius: var(--ff-radius-pill);
  border: 1px solid var(--ff-color-border);
  background: #fff;
  font: inherit;
  color: var(--ff-color-text);
  transition: border-color .15s ease, box-shadow .15s ease;
}
.ff-field__input:focus {
  outline: none;
  border-color: var(--ff-color-coral);
  box-shadow: 0 0 0 4px var(--ff-color-coral-shade-1);
}
```

### 7.4 Badge / pill (категории, метки)

```html
<span class="ff-badge ff-badge--coral">Новое</span>
<span class="ff-badge ff-badge--pink">Хит</span>
<span class="ff-badge ff-badge--purple">B2B</span>
```

```css
.ff-badge {
  display: inline-flex; align-items: center;
  padding: 6px 14px;
  border-radius: var(--ff-radius-pill);
  font-size: 13px; font-weight: 500; letter-spacing: 0.03em;
  color: var(--ff-color-deep-purpur);
}
.ff-badge--coral  { background: var(--ff-color-coral-shade-2); }
.ff-badge--pink   { background: var(--ff-color-soft-pink); }
.ff-badge--purple { background: var(--ff-color-soft-purple); }
.ff-badge--blue   { background: var(--ff-color-spring-blue); }
.ff-badge--beige  { background: var(--ff-color-comfy-beige); }
```

### 7.5 Hero-блок (типовая структура)

```html
<section class="ff-section ff-hero" style="background: var(--ff-color-coral-shade-1);">
  <div class="ff-container ff-hero__grid">
    <div class="ff-hero__copy">
      <span class="ff-badge ff-badge--coral">Для бизнеса</span>
      <h1>Откройте магазин на Flowwow</h1>
      <p class="ff-hero__lead">
        4500 продавцов уже зарабатывают на платформе. Подключение за один день, без вложений.
      </p>
      <div class="ff-hero__cta">
        <a class="ff-btn ff-btn--primary" href="#start">Начать</a>
        <a class="ff-btn ff-btn--ghost" href="#more">Как это работает</a>
      </div>
    </div>
    <div class="ff-hero__media">
      <!-- DROP: 3D-иллюстрация / продуктовый коллаж -->
    </div>
  </div>
</section>
```

```css
.ff-hero__grid {
  display: grid; gap: 48px;
  grid-template-columns: 1fr;
}
@media (min-width: 900px) {
  .ff-hero__grid { grid-template-columns: 1.1fr 1fr; align-items: center; }
}
.ff-hero__copy { display: grid; gap: 24px; }
.ff-hero__lead {
  font-size: var(--ff-text-xl);
  line-height: 1.3;
  color: var(--ff-color-text);
  max-width: 52ch;
}
.ff-hero__cta { display: flex; gap: 12px; flex-wrap: wrap; }
.ff-hero__media {
  aspect-ratio: 1 / 1;
  background: var(--ff-color-coral);
  border-radius: var(--ff-radius-xl);
}
```

### 7.6 Footer (минимальный)

```html
<footer class="ff-footer">
  <div class="ff-container ff-footer__grid">
    <!-- TODO: заменить на <img src="/assets/flowwow-logo-white.svg" alt="Flowwow" height="28" />
         когда получим .svg от админа платформы. Пока — текстовый placeholder. -->
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
}
.ff-footer__grid {
  display: grid; gap: 32px;
}
.ff-footer__logo {
  font-family: var(--ff-font-display);
  font-size: 24px; line-height: 1; letter-spacing: 0;
  color: #fff;
}
.ff-footer__nav { display: flex; flex-wrap: wrap; gap: 24px; }
.ff-footer__nav a { color: #fff; text-decoration: none; opacity: .85; }
.ff-footer__nav a:hover { opacity: 1; }
.ff-footer__legal { opacity: .6; }
</style>
```

---

## 8. Чек-лист для агента перед сдачей лендинга

Проходит **до** L2 (демонстрации оунеру на локальном preview — см. `./dev-workflow.md` §2.6: `make preview` только для статичной заглушки, иначе команда стека).

- [ ] Подключены CSS-переменные из раздела 2.6 и 3 в `:root`.
- [ ] `*, *::before, *::after { box-sizing: border-box; }` включён.
- [ ] Текст по умолчанию — `--ff-color-deep-purpur`, **не** `#000`.
- [ ] CTA — коралловый фон, белый текст, `border-radius: pill`. На странице **один** доминантный CTA-цвет (коралл); deep-purpur используется как neutral, не как второй акцент.
- [ ] Заголовки h1/h2 — дисплейный шрифт с `letter-spacing: 0` и плотным line-height.
- [ ] Параграфы — основной шрифт с `letter-spacing: 0.03em` (или 0.01em — см. caveat §3.5).
- [ ] Hero / большие секции имеют один пастельный или коралловый фон, не «винегрет».
- [ ] Углы карточек и изображений скруглены (≥ 16 px).
- [ ] Между секциями — большие воздушные отступы (≈ 96–128 px на десктопе).
- [ ] Иллюстрации и фото подставлены через placeholder’ы, если ассетов нет.
- [ ] Контраст текста на коралловом фоне проверен: body-текст коралловым — запрещён (см. §2.5). Коралл-как-текст — только display ≥24 px.
- [ ] Интерактивные элементы имеют `:focus-visible` стиль (кнопки, ссылки, поля).
- [ ] Логотип не растянут, не повёрнут, не перекрашен в произвольный цвет.
- [ ] Поднял лендинг в локальном preview (`make preview` — только для статичной заглушки, иначе команда стека; см. `./dev-workflow.md` §2.6) и проверил на 320 px (mobile) и 1440 px (desktop): hero не ломается, CTA остаётся видимым, текст не наезжает.

---

## 9. Что **не** указано в брендбуке (зоны риска)

Если на эти темы прилетает задача — спроси у пользователя или ставь явный TODO, не выдумывай:

- Сетка, breakpoints, контейнеры.
- Spacing scale.
- Радиусы и тени.
- Шкала размеров шрифта (display 1/2/3, body sizes).
- Стили состояний UI (hover / focus / disabled / loading / error).
- Иконография (стиль линий, weight, набор).
- Анимации и motion-принципы.
- Тёмная тема.
- Стили графиков, таблиц, инфографики.
- Tone of voice, словарь, табу-слова.
