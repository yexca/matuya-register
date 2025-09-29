first_page = """
<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8">
        <title>Get Matuya Account</title>
        <style>
            form {
                text-align: center;
                margin-top: 50px;
            }
            #output {
                width: min(320px, 92%);
                border-style: solid;
                border-color: #e5e7eb;
                border-radius: 8px;
                padding:12px 16px;
                margin: 20px auto;
            }

            .hidden { display: none; }

            /* 小圆圈 Spinner */
            .spinner {
                width: 16px; height: 16px;
                border: 2px solid #e5e7eb;          /* 背景圈 */
                border-top-color: #4b5563;          /* 运动的圈 */
                border-radius: 50%;
                animation: spin 2s linear infinite;
                display: inline-block;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            /* 无障碍：若用户偏好减少动画，就停掉旋转 */
            /* @media (prefers-reduced-motion: reduce) {
                .spinner { animation: none; }
            } */
        </style>
    </head>
    <body>
        <form id="reg-form" action="/register" method="post">
            <div style="margin: 10px;">
                按按钮获取，大概 40-60s 左右完成注册
            </div>
            <button id="start-btn" type="submit">开始注册</button>
        </form>

        <!-- result -->
         <div id="output" style="display: none;">
            <div style="margin: 6px 0;">
                <strong>账号: </strong>
                <code id="acc" style="padding: 2px 6px;"></code>
                <button type="button" data-copy-target="acc">复制账号</button>
            </div>
            <div style="margin: 6px 0;">
                <strong>密码: </strong>
                <code id="pwd" style="padding: 2px 6px;"></code>
                <button type="button" data-copy-target="pwd">复制密码</button>
            </div>
            <p id="status" style="margin-top:8px;">
                <span id="status-text"></span>
                <span id="inline-spin" class="spinner hidden" aria-hidden="true"></span>
            </p>
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
                btn.textContent = '注册中...';
                output.style.display = 'block';
                statusText.textContent = '正在获取信息...';
                inlineSpin.classList.add('spinner');
                form.setAttribute('aria-busy', 'true');
                accEl.textContent = '获取中...';
                pwdEl.textContent = '获取中...';

                try {
                    const res = await fetch(form.action, { method: 'POST', body: new FormData(form) });
                    if (!res.ok) throw new Error('HTTP' + res.status)
                    const data = await res.json();

                    accEl.textContent = data.account || '获取失败';
                    pwdEl.textContent = data.password || '获取失败';
                    statusText.textContent = '注册完成！';
                } catch (err) {
                    statusText.textContent = "注册失败" + err.message;
                } finally {
                    inlineSpin.classList.remove('spinner');
                    form.removeAttribute('aria-busy');
                    btn.disabled = false;
                    btn.textContent = original;
                }
            })

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

            // 复制函数：优先 Clipboard API，降级到 execCommand
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