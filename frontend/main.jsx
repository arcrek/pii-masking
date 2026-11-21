import { createRoot } from 'react-dom/client'
import './styles.css'

function LoginPreview() {
  return (
    <>
      <header className="brand tracking-wide">PII Shield</header>
      <main>
        <section aria-labelledby="title">
          <h1 id="title">Đăng nhập</h1>
          <p id="preview">Bản xem trước giao diện. Đăng nhập sẽ khả dụng khi kết nối API xác thực.</p>
          <form aria-describedby="preview">
            <fieldset disabled>
              <legend>Thông tin tài khoản</legend>
              <label htmlFor="username">Tên đăng nhập</label>
              <input id="username" autoComplete="username" required />
              <label htmlFor="password">Mật khẩu</label>
              <input id="password" type="password" autoComplete="current-password" required />
              <button type="submit">Đăng nhập</button>
            </fieldset>
          </form>
        </section>
      </main>
    </>
  )
}

createRoot(document.getElementById('root')).render(<LoginPreview />)
