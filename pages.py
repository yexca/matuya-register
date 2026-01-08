first_page = """
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="robots" content="noindex, nofollow">
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
        <p class="lead">大概 50s 左右完成注册，超时失败下方会有提示</p>
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

batch_page="""
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="robots" content="noindex, nofollow">
    <title>Batch Register Matuya</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
      :root {
        --radius: 12px;
        --primary: #111827;
        --bg: #fafafa;
      }
      html, body { height: 100%; }
      body {
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans CJK SC","Hiragino Sans","PingFang SC","Microsoft YaHei", Arial, sans-serif;
        font-size: 16px;
        line-height: 1.5;
        color: var(--primary);
        background: var(--bg);
        padding: 16px;
      }

      .container {
        max-width: 600px;
        margin: 0 auto;
      }

      /* 表单区域 */
      form {
        text-align: center;
        margin-top: 12px;
        padding: 20px;
        background: #fff;
        border: 1px solid #e5e7eb;
        border-radius: var(--radius);
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
      }

      .lead {
        margin: 6px 0 14px;
        color: #6b7280;
        font-size: 0.95rem;
      }

      /* 输入控件组 */
      .input-group {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 12px;
        margin-bottom: 16px;
      }

      select {
        padding: 8px 12px;
        font-size: 1rem;
        border: 1px solid #d1d5db;
        border-radius: 8px;
        background-color: #fff;
        cursor: pointer;
      }

      .btn {
        width: 100%;
        padding: 12px 16px;
        border: 0;
        border-radius: var(--radius);
        background: var(--primary);
        color: #fff;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        transition: opacity 0.2s;
      }
      .btn:hover { opacity: 0.9; }
      .btn[disabled] { opacity: 0.6; cursor: not-allowed; }

      /* 结果列表区域 */
      #output-area {
        margin-top: 20px;
      }

      /* 单个结果卡片 */
      .result-card {
        background: #fff;
        border: 1px solid #e5e7eb;
        border-radius: var(--radius);
        padding: 16px;
        margin-bottom: 12px;
        position: relative;
        animation: slideIn 0.3s ease-out;
      }
      @keyframes slideIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

      .result-card.success { border-left: 5px solid #10b981; }
      .result-card.fail { border-left: 5px solid #ef4444; }

      .row {
        margin: 8px 0;
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
      }

      code {
        padding: 4px 8px;
        background: #f3f4f6;
        border-radius: 6px;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        word-break: break-all;
        color: #4b5563;
      }

      .copy-btn {
        padding: 6px 10px;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        background: #fff;
        font-size: 0.85rem;
        cursor: pointer;
        color: #374151;
      }
      .copy-btn:hover { background: #f9fafb; border-color: #d1d5db; }

      .status-badge {
        font-size: 0.85rem;
        font-weight: bold;
        padding: 2px 8px;
        border-radius: 4px;
        margin-bottom: 8px;
        display: inline-block;
      }
      .status-success { background: #d1fae5; color: #065f46; }
      .status-fail { background: #fee2e2; color: #991b1b; }
      .error-msg { color: #ef4444; font-size: 0.9rem; }

      /* 顶部状态提示 */
      #global-status {
        text-align: center;
        color: #6b7280;
        margin-bottom: 10px;
        font-size: 0.9rem;
        min-height: 24px;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <form id="reg-form">
        <h2>批量账号注册</h2>
        <p class="lead">单次耗时约 50s，多线程并发执行</p>
        
        <div class="input-group">
            <label for="count-select">生成数量：</label>
            <select id="count-select" name="count">
                <option value="1" selected>1 个</option>
                <option value="2">2 个</option>
                <option value="3">3 个</option>
                <option value="4">4 个</option>
                <option value="5">5 个</option>
            </select>
        </div>

        <button id="start-btn" type="submit" class="btn">开始注册</button>
      </form>

      <div id="global-status"></div>
      <div id="output-area"></div>
    </div>

    <script>
      const form = document.getElementById('reg-form');
      const btn = document.getElementById('start-btn');
      const outputArea = document.getElementById('output-area');
      const globalStatus = document.getElementById('global-status');
      const countSelect = document.getElementById('count-select');

      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // 1. 准备 UI
        const count = countSelect.value;
        const originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = `正在注册 ${count} 个账号...`;
        globalStatus.textContent = '任务运行中，请耐心等待...';
        outputArea.innerHTML = ''; // 清空旧结果

        try {
          // 2. 发起请求 (注意 URL 改为了 /register_batch)
          const res = await fetch('/register_batch', { 
            method: 'POST', 
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ count: parseInt(count) }) 
          });

          if (!res.ok) throw new Error('HTTP ' + res.status);
          
          const data = await res.json();
          
          // 3. 渲染结果
          globalStatus.textContent = `完成！成功: ${data.success_count} / 总计: ${data.total_requested}`;
          renderResults(data.details);

        } catch (err) {
          globalStatus.textContent = '请求发生错误';
          outputArea.innerHTML = `<div class="result-card fail"><p class="error-msg">系统错误：${err.message}</p></div>`;
        } finally {
          btn.disabled = false;
          btn.textContent = originalText;
        }
      });

      // 渲染列表函数
      function renderResults(details) {
        if (!details || details.length === 0) return;

        details.forEach((item, index) => {
            const isSuccess = item.success;
            const card = document.createElement('div');
            card.className = `result-card ${isSuccess ? 'success' : 'fail'}`;

            if (isSuccess) {
                card.innerHTML = `
                    <div class="status-badge status-success">账号 #${index + 1} 成功</div>
                    <div class="row">
                        <strong>账号：</strong>
                        <code>${item.account}</code>
                        <button type="button" class="copy-btn" data-copy-val="${item.account}">复制</button>
                    </div>
                    <div class="row">
                        <strong>密码：</strong>
                        <code>${item.password}</code>
                        <button type="button" class="copy-btn" data-copy-val="${item.password}">复制</button>
                    </div>
                `;
            } else {
                card.innerHTML = `
                    <div class="status-badge status-fail">账号 #${index + 1} 失败</div>
                    <div class="row">
                        <strong>账号：</strong>
                        <code>${item.account}</code>
                    </div>
                    <p class="error-msg">原因：${item.msg || '未知错误'}</p>
                `;
            }
            outputArea.appendChild(card);
        });
      }

      // 复制功能的事件委托
      document.addEventListener('click', async (e) => {
        const b = e.target.closest('button[data-copy-val]');
        if (!b) return;

        const text = b.getAttribute('data-copy-val');
        if (!text) return;

        try {
          await copyText(text);
          const old = b.textContent;
          b.textContent = 'OK';
          b.style.color = '#10b981';
          b.style.borderColor = '#10b981';
          setTimeout(() => {
              b.textContent = old;
              b.style.color = '';
              b.style.borderColor = '';
          }, 1000);
        } catch (err) {
          alert('复制失败：' + err.message);
        }
      });

      async function copyText(text) {
        if (navigator.clipboard && window.isSecureContext) {
          return navigator.clipboard.writeText(text);
        } else {
          // 兼容旧浏览器的回退方案
          const ta = document.createElement('textarea');
          ta.value = text;
          ta.style.position = 'fixed';
          ta.style.left = '-9999px';
          document.body.appendChild(ta);
          ta.focus();
          ta.select();
          document.execCommand('copy');
          document.body.removeChild(ta);
        }
      }
    </script>
  </body>
</html>
"""