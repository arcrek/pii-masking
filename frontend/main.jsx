import { useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

function Brand() {
  return <span className="brand"><i className="mark" aria-hidden="true"><b/><b/><b/></i>PII Shield</span>
}

function FlowerSprig({ placement }) {
  return (
    <svg className={`sprig sprig--${placement}`} viewBox="0 0 64 100" aria-hidden="true" focusable="false">
      <g stroke="#697959" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <path fill="none" d="M19 94Q33 66 31 28M29 64Q42 58 48 44" />
        <path fill="#b1bd99" d="M25 78Q8 70 9 57Q25 63 25 78ZM31 54Q16 47 17 36Q31 42 31 54ZM38 57Q37 43 45 39Q48 50 38 57Z" />
      </g>
      <g transform="translate(31 22)" fill="#f8ecd9" stroke="#a87e61" strokeWidth="1.2">
        {[0, 72, 144, 216, 288].map(angle => (
          <ellipse key={angle} cy="-6" rx="3.8" ry="6.2" transform={`rotate(${angle})`} />
        ))}
        <circle r="3.4" fill="#c89860" />
      </g>
      <ellipse cx="49" cy="42" rx="3" ry="5" fill="#c5967c" transform="rotate(26 49 42)" />
    </svg>
  )
}

function DocumentSample() {
  const [masked, setMasked] = useState(true)
  return (
    <section className="sample" aria-label="Minh họa ẩn thông tin trong tài liệu">
      <div className="drawing" data-masked={masked}>
        <FlowerSprig placement="upper" />
        <FlowerSprig placement="lower" />
        <div className="folder" aria-hidden="true" />
        <article className="sheet">
          <div className="sheet-head"><span>HỒ SƠ DỊCH VỤ</span><span>01 / 01</span></div>
          <h2>Thỏa thuận<br/>dịch vụ</h2>
          <div className="rules" aria-hidden="true"/>
          <dl className={masked ? 'masked' : ''}>
            <div><dt>Bên A</dt><dd>{masked ? 'Người 01' : 'An Nguyễn'}</dd></div>
            <div><dt>Email</dt><dd>{masked ? 'Email 04' : 'an@example.com'}</dd></div>
          </dl>
          <div className="sheet-foot"><span>Hợp đồng mẫu</span><span>PII Shield</span></div>
        </article>
      </div>
      <div className="switch" role="group" aria-label="Chế độ xem tài liệu mẫu">
        <button type="button" aria-pressed={!masked} onClick={() => setMasked(false)}>Bản gốc</button>
        <button type="button" aria-pressed={masked} onClick={() => setMasked(true)}>Đã ẩn</button>
      </div>
    </section>
  )
}

function LoginPreview() {
  return (
    <div className="shell">
      <header><Brand/><span className="studio">Studio kiểm duyệt PDF</span></header>
      <main>
        <DocumentSample/>
        <section className="login" aria-labelledby="title">
          <h1 id="title">Đăng nhập<br/><em>vào Studio.</em></h1>
          <p id="preview">Giao diện xem trước. Đăng nhập sẽ khả dụng khi Studio kết nối dịch vụ xác thực.</p>
          <form aria-describedby="preview">
            <fieldset disabled>
              <label htmlFor="username">Tên đăng nhập</label>
              <input id="username" autoComplete="username" placeholder="Tên tài khoản" />
              <label htmlFor="password">Mật khẩu</label>
              <input id="password" type="password" autoComplete="current-password" />
              <button className="submit" type="submit">Đăng nhập <span aria-hidden="true">↗</span></button>
            </fieldset>
          </form>
        </section>
      </main>
    </div>
  )
}

createRoot(document.getElementById('root')).render(<LoginPreview />)
