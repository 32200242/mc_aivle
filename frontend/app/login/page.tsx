"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("counselor");
  const [password, setPassword] = useState("demo");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true); setError("");
    try {
      const user = await login(username, password);
      router.push(user.role.includes("admin") ? "/admin/dashboard" : "/counselor");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "로그인에 실패했습니다.");
    } finally { setLoading(false); }
  }
  return (
    <main className="login-page">
      <section className="login-hero">
        <div className="hero-copy">
          <h1>가족의 <em>행복</em>, 함께 만드는 <em>미래</em></h1>
          <p>AI 기반 상담·교육·성과관리 통합 플랫폼</p>
        </div>
        <div className="family-illustration" aria-hidden="true">
          <span className="person parent-one">●</span><span className="person parent-two">●</span>
          <span className="person child-one">●</span><span className="person child-two">●</span>
          <b>♥</b>
        </div>
        <div className="agency-lockup"><span><img src="/brand/kihf-logo.png" alt="한국건강가정진흥원" /><strong>한국건강가정진흥원</strong></span><i>×</i><span><img src="/brand/family-center-logo.png" alt="가족센터" /><strong>가족센터</strong></span></div>
      </section>
      <section className="login-card">
        <div className="login-logo"><img src="/brand/family-center-logo.png" alt="가족센터" /><b>가족센터</b></div>
        <h2>가족센터 통합 지원 시스템</h2>
        <form onSubmit={submit}>
          <label><span>♙</span><input aria-label="아이디" value={username} onChange={e => setUsername(e.target.value)} placeholder="아이디를 입력해주세요" /></label>
          <label><span>▣</span><input aria-label="비밀번호" type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="비밀번호를 입력해주세요" /></label>
          <div className="login-options"><span>□ 아이디 저장</span><span>아이디 / 비밀번호 찾기</span></div>
          {error && <p className="form-error">{error}</p>}
          <button className="primary wide" disabled={loading}>{loading ? "확인 중…" : "로그인"}</button>
        </form>
        <div className="divider"><span>또는</span></div>
        <button className="certificate">▦ 공동인증서 로그인</button>
        <div className="security-note"><b>◇ 보안 안내</b><small>개인정보 보호를 위해 로그인 후 브라우저를 닫아주세요.</small></div>
        <div className="demo-accounts"><b>프로토타입 계정</b><span>상담사: counselor / demo</span><span>관리자: admin / demo</span></div>
      </section>
    </main>
  );
}
