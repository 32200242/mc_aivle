"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { login } from "@/lib/api";

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
  return (
    <main className="login-page">
      <div className="login-shell">
        <section className="login-hero">
          <div className="login-agencies"><span><img src="/brand/kihf-logo.png" alt="한국건강가정진흥원" /><b>한국건강가정진흥원</b></span><span><img src="/brand/family-center-logo.png" alt="가족센터" /><b>가족센터</b><small>함께하는 가족, 행복한 사회</small></span></div>
          <div className="family-illustration" aria-hidden="true">
            <span className="person parent-one">●</span><span className="person parent-two">●</span>
            <span className="person child-one">●</span><span className="person child-two">●</span>
            <b>♥</b>
          </div>
          <p className="login-mission">가족상담과 현장 운영을 하나로 잇는<br />더 나은 가족서비스의 시작</p>
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
          <div className="login-recovery"><button type="button">아이디 찾기</button><button type="button">비밀번호 찾기</button></div>
          <div className="divider"><span>또는</span></div>
          <button type="button" className="certificate">▦ 공동인증서 로그인</button>
          <div className="security-note"><b>◇ 보안 안내</b><small>개인정보 보호를 위해 이용 후 반드시 로그아웃해 주세요.</small></div>
          <small className="login-copyright">© 한국건강가정진흥원. All Rights Reserved.</small>
        </section>
      </div>
    </main>
  );
}
