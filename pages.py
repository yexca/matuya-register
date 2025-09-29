first_page = """
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <title>Get Matuya Account</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
      :root {
        /* 全局尺寸基准，移动端易读 */
        --radius: 12px;
      }
      html, body { height: 100%; }
      body {
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans CJK SC","Hiragino Sans","PingFang SC","Microsoft YaHei", Arial, sans-serif;
        font-size: 16px;
        line-height: 1.5;
        color: #111827;
        background: #fafafa;
        padding: 16px;
      }

      /* 把内容宽度限制在合适范围并居中；在手机上就是左右留白 */
      .container {
        max-width: 560px;
        margin: 0 auto;
      }

      form {
        text-align: center;
        margin-top: 12px;
        padding: 16px;
        background: #fff;
        border: 1px solid #e5e7eb;
        border-radius: var(--radius);
      }

      .lead {
        margin: 6px 0 14px;
        color: #374151;
      }

      /* 按钮做成易点按（高度>=44px，宽度尽量占满） */
      .btn {
        width: 100%;
        display: inline-block;
        padding: 12px 16px;
        border: 0;
        border-radius: var(--radius);
        background: #111827;
        color: #fff;
        font-size: 1rem;
        line-height: 1.2;
        cursor: pointer;
      }
      .btn[disabled] { opacity: .6; cursor: not-allowed; }

      #output {
        width: 100%;
        max-width: 560px;
        border: 1px solid #e5e7eb;
        border-radius: var(--radius);
        padding: 12px 16px;
        margin: 16px auto 0;
        background: #fff;
      }

      .row { margin: 8px 0; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
      code {
        padding: 4px 8px;
        background: #f3f4f6;
        border-radius: 8px;
        word-break: break-all;
      }
      .copy-btn {
        padding: 8px 10px;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        background: #f9fafb;
        font-size: .95rem;
      }

      .hidden { display: none; }

      /* 小圆圈 Spinner */
      .spinner {
        width: 16px; height: 16px;
        border: 2px solid #e5e7eb;
        border-top-color: #4b5563;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        display: inline-block;
        vertical-align: -3px;
      }
      @keyframes spin { to { transform: rotate(360deg); } }
      @media (prefers-reduced-motion: reduce) { .spinner { animation: none; } }

      /* 小屏优化：把代码块撑满一行，复制键换行靠后 */
      @media (max-width: 420px) {
        .row { align-items: stretch; }
        .row code { flex: 1 1 100%; }
        .copy-btn { width: 100%; }
      }
    </style>
  </head>
  <body>
    <div class="container">
      <form id="reg-form" action="/register" method="post">
        <p class="lead">大概 40s 到 60s 左右完成注册</p>
        <button id="start-btn" type="submit" class="btn">开始注册</button>
      </form>

      <div id="output" style="display:none;">
        <div class="row">
          <strong>账号：</strong>
          <code id="acc"></code>
          <button type="button" class="copy-btn" data-copy-target="acc">复制账号</button>
        </div>
        <div class="row">
          <strong>密码：</strong>
          <code id="pwd"></code>
          <button type="button" class="copy-btn" data-copy-target="pwd">复制密码</button>
        </div>
        <p id="status" style="margin-top:8px;">
          <span id="status-text"></span>
          <span id="inline-spin" class="hidden" aria-hidden="true"></span>
        </p>
      </div>
    </div>

    <script>
      const form = document.getElementById('reg-form');
      const btn = document.getElementById('start-btn');
      const output = document.getElementById('output');
      const statusText = document.getElementById('status-text');
      const inlineSpin = document.getElementById('inline-spin');
      const accEl = document.getElementById('acc');
      const pwdEl = document.getElementById('pwd');

      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const original = btn.textContent;
        btn.disabled = true;
        btn.textContent = '注册中…';
        output.style.display = 'block';
        statusText.textContent = '正在获取信息…';
        inlineSpin.classList.add('spinner');
        form.setAttribute('aria-busy', 'true');
        accEl.textContent = '获取中…';
        pwdEl.textContent = '获取中…';

        try {
          const res = await fetch(form.action, { method: 'POST', body: new FormData(form) });
          if (!res.ok) throw new Error('HTTP ' + res.status);
          const data = await res.json();

          accEl.textContent = data.account || '获取失败';
          pwdEl.textContent = data.password || '获取失败';
          statusText.textContent = '注册完成！';
        } catch (err) {
          statusText.textContent = '注册失败：' + err.message;
        } finally {
          inlineSpin.classList.remove('spinner');
          form.removeAttribute('aria-busy');
          btn.disabled = false;
          btn.textContent = original;
        }
      });

      // 单独复制：事件委托
      document.addEventListener('click', async (e) => {
        const b = e.target.closest('button[data-copy-target]');
        if (!b) return;

        const id = b.getAttribute('data-copy-target');
        const text = document.getElementById(id)?.textContent ?? '';
        if (!text) return;

        try {
          await copyText(text);
          const old = b.textContent;
          b.textContent = '已复制 ✓';
          setTimeout(() => (b.textContent = old), 1200);
        } catch (err) {
          alert('复制失败：' + err.message);
        }
      });

      // 复制函数
      async function copyText(text) {
        if (navigator.clipboard && window.isSecureContext) {
          return navigator.clipboard.writeText(text);
        } else {
          const ta = document.createElement('textarea');
          ta.value = text;
          ta.style.position = 'fixed';
          ta.style.left = '-9999px';
          document.body.appendChild(ta);
          ta.focus();
          ta.select();
          const ok = document.execCommand('copy');
          document.body.removeChild(ta);
          if (!ok) throw new Error('execCommand 复制失败');
        }
      }
    </script>
  </body>
</html>
"""