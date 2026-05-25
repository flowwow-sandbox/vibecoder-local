<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${SANDBOX_SLUG} — твоя первая страница</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
      background: #f5f5f7;
      color: #1d1d1f;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 2rem;
    }

    .card {
      background: #ffffff;
      border-radius: 18px;
      padding: 3rem 3.5rem;
      max-width: 560px;
      width: 100%;
      box-shadow: 0 4px 24px rgba(0,0,0,0.08);
      text-align: center;
    }

    .badge {
      display: inline-block;
      background: #e8f9ef;
      color: #1a8a3e;
      font-size: 0.85rem;
      font-weight: 600;
      letter-spacing: 0.02em;
      padding: 0.3rem 0.9rem;
      border-radius: 100px;
      margin-bottom: 1.6rem;
    }

    h1 {
      font-size: 2rem;
      font-weight: 700;
      line-height: 1.2;
      margin-bottom: 1rem;
    }

    .slug {
      color: #6e40c9;
    }

    p {
      font-size: 1.05rem;
      line-height: 1.65;
      color: #48484a;
      margin-bottom: 1rem;
    }

    p:last-child { margin-bottom: 0; }

    code {
      background: #f2f2f7;
      border-radius: 6px;
      padding: 0.15em 0.4em;
      font-family: 'SF Mono', SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.92em;
      color: #1d1d1f;
    }
  </style>
</head>
<body>
  <div class="card">
    <span class="badge">🟢 всё работает</span>
    <h1>Hello world!</h1>
    <p>Это твоё пространство в «песочнице» — всё работает.</p>
    <p>Дальше открой Claude Code или Codex
      в папке <code>${SANDBOX_SLUG}</code> и попроси создать то,
      что тебе нужно: «сделай мне таск-трекер»,
      «давай сделаем сервис тайного Санты»,
      «давай построим дашборд с данными».</p>
    <p>Не уверен, с чего начать — так и добавь:
      «задай мне вопросы, чтобы понять, что мне нужно».</p>
  </div>
</body>
</html>
