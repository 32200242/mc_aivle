"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { login } from "@/lib/api";

const publicDemoMode = process.env.NEXT_PUBLIC_PUBLIC_DEMO === "true";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true); setError("");
    try {
      const user = await login(username, password);
      router.push(user.role === "central_admin" ? "/admin/dashboard" : "/counselor");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "로그인에 실패했습니다.");
    } finally { setLoading(false); }
  }
  async function enterDemo(account: "admin" | "counselor") {
    setUsername(account);
    setPassword("demo");
    setLoading(true);
    setError("");
    try {
      const user = await login(account, "demo");
      router.push(user.role === "central_admin" ? "/admin/dashboard" : "/counselor");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "시연 계정 로그인에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }
  return (
    <main className="login-page">
      <div className="login-shell">
        <section className="login-hero">
          <div className="login-agencies"><span><img src="/brand/kihf-logo.png" alt="한국건강가정진흥원" /><b>한국건강가정진흥원</b></span><span><img src="/brand/family-center-logo.png" alt="가족센터" /><b>가족센터</b><small>함께하는 가족, 행복한 사회</small></span></div>
          <div className="family-illustration" aria-hidden="true">
            <img className="family-heart-mark" src="/brand/login-family-mark.png?v=20260818-upscaled" alt="" />
          </div>
          <p className="login-mission">가족상담과 현장 운영을 하나로 잇는<br />더 나은 가족서비스의 시작</p>
          <strong className="maum-wordmark">MA:UM</strong>
        </section>
        <section className="login-card">
          <h2>가족센터 통합 지원 시스템</h2>
          <form onSubmit={submit}>
            <noscript><p className="form-error">로그인에는 브라우저 JavaScript가 필요합니다. JavaScript를 허용한 뒤 새로고침하세요.</p></noscript>
            <label><span>♙</span><input aria-label="아이디" autoComplete="username" value={username} onChange={e => setUsername(e.target.value)} placeholder="상담사 ID 또는 관리자 계정" /></label>
            <label><span>▣</span><input aria-label="비밀번호" autoComplete="current-password" type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="비밀번호를 입력하세요" /></label>
            {error && <p className="form-error">{error}</p>}
            <button type="submit" className="primary wide" disabled={loading}>{loading ? "확인 중…" : "LOGIN"}</button>
          </form>
          {publicDemoMode && <section className="public-demo-login">
            <div><b>공개 시연 모드</b><small>합성 데이터와 고정 응답으로 실제 화면 흐름을 확인합니다.</small></div>
            <p>교육생 제안용 비공식 프로토타입이며 실제 기관 서비스가 아닙니다. 실제 개인정보는 입력하지 마세요.</p>
            <ul className="public-demo-status">
              <li><b>현재 실행</b><span>대시보드 · 합성 사례 · 결정론적 코파일럿 · 교육 영상</span></li>
              <li><b>GPU 연결 시</b><span>생성형 AI · OCR · 음성 · 영상 확장</span></li>
            </ul>
            <div className="public-demo-buttons">
              <button type="button" onClick={() => void enterDemo("counselor")} disabled={loading}>상담사 시연 시작</button>
              <button type="button" onClick={() => void enterDemo("admin")} disabled={loading}>관리자 시연 시작</button>
            </div>
            <a className="public-demo-doc" href="/docs/DX_05조_기술명세서.md" target="_blank" rel="noreferrer">전체 기술명세서 보기 ↗</a>
          </section>}
          <div className="login-recovery"><button type="button">아이디 찾기</button><button type="button">비밀번호 찾기</button></div>
          <div className="divider"><span>또는</span></div>
          <button type="button" className="certificate">▦ 공동인증서 로그인</button>
          <div className="security-note"><b>◇ 보안 안내</b><small>개인정보 보호를 위해 이용 후 반드시 로그아웃해 주세요.</small></div>
          <small className="login-copyright">{publicDemoMode ? "교육생 제안용 비공식 프로토타입 · 기관 승인·운영 서비스 아님" : "© 한국건강가정진흥원. All Rights Reserved."}</small>
        </section>
      </div>
    </main>
  );
}
