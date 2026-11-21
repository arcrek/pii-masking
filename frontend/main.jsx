import { useEffect, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'
import './text-motion.css'

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

function DecodeText({ text, enabled }) {
  if (!enabled) return text
  return (
    <>
      <span className="sr-only">{text}</span>
      <span aria-hidden="true" key={text}>
        {Array.from(text).map((letter, index) => letter === ' ' ? ' ' : (
          <span className="glyph" key={index} style={{ '--delay': `${index * 32}ms` }}>
            <span>{letter}</span>
          </span>
        ))}
      </span>
    </>
  )
}

const mouseMotionQuery = '(any-hover: hover) and (any-pointer: fine) and (prefers-reduced-motion: no-preference)'

function usePaperTilt(enabled) {
  const ref = useRef(null)
  useEffect(() => {
    if (!enabled) return
    const paper = ref.current
    const media = window.matchMedia(mouseMotionQuery)
    const target = { x: 0, y: 0 }
    const angle = { x: 0, y: 0 }
    const speed = { x: 0, y: 0 }
    let frame = 0
    let previous = 0

    function tick(now) {
      const dt = Math.min((now - previous) / 1000, 1 / 30)
      previous = now
      let moving = false
      for (const axis of ['x', 'y']) {
        const distance = target[axis] - angle[axis]
        speed[axis] += (180 * distance - 23 * speed[axis]) * dt
        angle[axis] += speed[axis] * dt
        moving ||= Math.abs(distance) > .005 || Math.abs(speed[axis]) > .04
      }
      if (!moving) {
        Object.assign(angle, target)
        speed.x = speed.y = 0
      }
      const degrees = Math.hypot(angle.x, angle.y)
      paper.style.rotate = degrees ? `${angle.x} ${angle.y} 0 ${degrees}deg` : ''
      frame = moving ? requestAnimationFrame(tick) : 0
    }
    function aim(x, y) {
      target.x = x
      target.y = y
      if (!frame) {
        previous = performance.now()
        frame = requestAnimationFrame(tick)
      }
    }
    function follow(event) {
      if (!media.matches || event.pointerType !== 'mouse') return
      const box = paper.getBoundingClientRect()
      const offset = ratio => Math.max(-1, Math.min(1, 2 * ratio - 1))
      aim(-2.5 * offset((event.clientY - box.top) / box.height),
          2.5 * offset((event.clientX - box.left) / box.width))
    }
    const release = () => aim(0, 0)
    function reset() {
      cancelAnimationFrame(frame)
      frame = 0
      target.x = target.y = angle.x = angle.y = speed.x = speed.y = 0
      paper.style.rotate = ''
    }
    paper.addEventListener('pointermove', follow)
    paper.addEventListener('pointerleave', release)
    paper.addEventListener('pointercancel', release)
    window.addEventListener('blur', reset)
    media.addEventListener('change', reset)
    return () => {
      reset()
      paper.removeEventListener('pointermove', follow)
      paper.removeEventListener('pointerleave', release)
      paper.removeEventListener('pointercancel', release)
      window.removeEventListener('blur', reset)
      media.removeEventListener('change', reset)
    }
  }, [enabled])
  return ref
}

function DocumentSample({ motion }) {
  const [masked, setMasked] = useState(true)
  const paperRef = usePaperTilt(motion)
  return (
    <section className="sample" aria-label="Minh họa ẩn thông tin trong tài liệu">
      <div className="drawing" data-masked={masked}>
        <FlowerSprig placement="upper" />
        <FlowerSprig placement="lower" />
        <div className="folder" aria-hidden="true" />
        <article className="sheet" ref={paperRef}>
          <div className="sheet-head"><span>HỒ SƠ DỊCH VỤ</span><span>01 / 01</span></div>
          <h2>Thỏa thuận<br/>dịch vụ</h2>
          <div className="rules" aria-hidden="true"/>
          <dl className={masked ? 'masked' : ''}>
            <div><dt>Bên A</dt><dd><DecodeText enabled={motion} text={masked ? 'Người 01' : 'An Nguyễn'} /></dd></div>
            <div><dt>Email</dt><dd><DecodeText enabled={motion} text={masked ? 'Email 04' : 'an@example.com'} /></dd></div>
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

function PaperWatermark() {
  const trace = useRef(null)

  useEffect(() => {
    const shell = trace.current.parentElement
    const media = window.matchMedia(mouseMotionQuery)
    function hide() {
      shell.removeAttribute('data-revealing')
    }

    function follow(event) {
      if (!media.matches || event.pointerType !== 'mouse') return hide()
      shell.style.setProperty('--reveal-x', `${event.clientX}px`)
      shell.style.setProperty('--reveal-y', `${event.clientY}px`)
      shell.dataset.revealing = ''
    }

    window.addEventListener('pointermove', follow, { passive: true })
    document.documentElement.addEventListener('pointerleave', hide)
    window.addEventListener('blur', hide)
    media.addEventListener('change', hide)
    return () => {
      hide()
      window.removeEventListener('pointermove', follow)
      document.documentElement.removeEventListener('pointerleave', hide)
      window.removeEventListener('blur', hide)
      media.removeEventListener('change', hide)
    }
  }, [])

  return <div className="paper-watermark" aria-hidden="true" ref={trace} />
}

function LoginPreview() {
  const [motion, setMotion] = useState(() => {
    try {
      return localStorage.getItem('pii-login-text-motion') !== 'off'
    } catch {
      return true
    }
  })

  function toggleMotion() {
    setMotion(!motion)
    try {
      localStorage.setItem('pii-login-text-motion', motion ? 'off' : 'on')
    } catch {
      // The switch still works for this visit when storage is unavailable.
    }
  }

  return (
    <div className="shell" data-motion={motion ? 'on' : 'off'}>
      {motion && <PaperWatermark />}
      <header>
        <Brand/>
        <span className="studio">Studio kiểm duyệt PDF</span>
        <button type="button" className="motion-switch" aria-label="Chuyển động chữ và nền" aria-pressed={motion} onClick={toggleMotion}>
          Chuyển động · {motion ? 'Bật' : 'Tắt'}
        </button>
      </header>
      <main>
        <section className="login" aria-labelledby="title">
          <h1 id="title">Đăng nhập<br/><em>vào <DecodeText enabled={motion} text="Studio." /></em></h1>
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
        <DocumentSample motion={motion}/>
      </main>
    </div>
  )
}

createRoot(document.getElementById('root')).render(<LoginPreview />)
