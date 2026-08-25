"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import {
  getRecoveryCenters,
  getRecoveryCounselors,
  login,
  type RecoveryCenter,
  type RecoveryCounselor,
} from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [recoveryDialog, setRecoveryDialog] = useState<"username" | "password" | null>(null);
  const [recoveryCenters, setRecoveryCenters] = useState<RecoveryCenter[]>([]);
  const [selectedCenterId, setSelectedCenterId] = useState("");
  const [recoveryCounselors, setRecoveryCounselors] = useState<RecoveryCounselor[]>([]);
  const [selectedCounselorId, setSelectedCounselorId] = useState("");
  const [recoveredCounselor, setRecoveredCounselor] = useState<RecoveryCounselor | null>(null);
  const [recoveryError, setRecoveryError] = useState("");
  const [recoveryLoading, setRecoveryLoading] = useState(false);

  useEffect(() => {
    if (!recoveryDialog) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setRecoveryDialog(null);
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [recoveryDialog]);

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

  async function openUsernameRecovery() {
    setRecoveryError("");
    setSelectedCenterId("");
    setRecoveryCounselors([]);
    setSelectedCounselorId("");
    setRecoveredCounselor(null);
    setRecoveryDialog("username");
    setRecoveryLoading(true);
    try {
      const centers = await getRecoveryCenters();
      setRecoveryCenters(centers);
      if (!centers.length) setRecoveryError("선택할 수 있는 센터가 없습니다.");
    } catch (reason) {
      setRecoveryError(reason instanceof Error ? reason.message : "센터 목록을 불러오지 못했습니다.");
    } finally {
      setRecoveryLoading(false);
    }
  }

  async function selectRecoveryCenter(centerId: string) {
    setSelectedCenterId(centerId);
    setRecoveryCounselors([]);
    setSelectedCounselorId("");
    setRecoveredCounselor(null);
    setRecoveryError("");
    if (!centerId) return;
    setRecoveryLoading(true);
    try {
      const counselors = await getRecoveryCounselors(centerId);
      setRecoveryCounselors(counselors);
      if (!counselors.length) setRecoveryError("이 센터에 등록된 시연용 상담사 계정이 없습니다.");
    } catch (reason) {
      setRecoveryError(reason instanceof Error ? reason.message : "상담사 목록을 불러오지 못했습니다.");
    } finally {
      setRecoveryLoading(false);
    }
  }

  function submitUsernameRecovery(event: FormEvent) {
    event.preventDefault();
    const counselor = recoveryCounselors.find((item) => item.counselor_id === selectedCounselorId) ?? null;
    setRecoveredCounselor(counselor);
    if (!counselor) setRecoveryError("상담사를 선택해 주세요.");
  }

  function useRecoveredUsername(value: string) {
    setUsername(value);
    setRecoveryDialog(null);
  }

  function useDemoPassword() {
    setPassword("demo");
    setRecoveryDialog(null);
  }

  const selectedRecoveryCenter = recoveryCenters.find((center) => center.center_id === selectedCenterId);

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
          <div className="login-recovery"><button type="button" onClick={() => void openUsernameRecovery()}>아이디 찾기</button><button type="button" onClick={() => setRecoveryDialog("password")}>비밀번호 찾기</button></div>
          <div className="divider"><span>또는</span></div>
          <button type="button" className="certificate">▦ 공동인증서 로그인</button>
          <div className="security-note"><b>◇ 보안 안내</b><small>개인정보 보호를 위해 이용 후 반드시 로그아웃해 주세요.</small></div>
          <small className="login-copyright">© 한국건강가정진흥원. All Rights Reserved.</small>
        </section>
      </div>
      {recoveryDialog && (
        <div
          className="recovery-backdrop"
          onMouseDown={(event) => {
            if (event.currentTarget === event.target) setRecoveryDialog(null);
          }}
        >
          <section
            className="recovery-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="recovery-dialog-title"
          >
            <button type="button" className="recovery-close" onClick={() => setRecoveryDialog(null)} aria-label="닫기">×</button>
            {recoveryDialog === "username" ? (
              <>
                <h2 id="recovery-dialog-title">아이디 찾기</h2>
                <p className="recovery-description">소속 센터와 상담사를 차례로 선택하면 시연용 아이디를 확인할 수 있습니다.</p>
                <form className="recovery-form" onSubmit={submitUsernameRecovery}>
                  <label htmlFor="recovery-center">센터명</label>
                  <select
                    id="recovery-center"
                    autoFocus
                    value={selectedCenterId}
                    onChange={(event) => void selectRecoveryCenter(event.target.value)}
                    disabled={recoveryLoading && !selectedCenterId}
                    required
                  >
                    <option value="">{recoveryLoading && !recoveryCenters.length ? "센터 목록 불러오는 중…" : "센터를 선택하세요"}</option>
                    {recoveryCenters.map((center) => <option key={center.center_id} value={center.center_id}>[{center.region_name}] {center.center_name}</option>)}
                  </select>
                  <label htmlFor="recovery-counselor">상담사 이름</label>
                  <select
                    id="recovery-counselor"
                    value={selectedCounselorId}
                    onChange={(event) => {
                      setSelectedCounselorId(event.target.value);
                      setRecoveredCounselor(null);
                      setRecoveryError("");
                    }}
                    disabled={!selectedCenterId || recoveryLoading}
                    required
                  >
                    <option value="">{recoveryLoading && selectedCenterId ? "상담사 목록 불러오는 중…" : "상담사를 선택하세요"}</option>
                    {recoveryCounselors.map((counselor) => <option key={counselor.counselor_id} value={counselor.counselor_id}>{counselor.counselor_name}</option>)}
                  </select>
                  <p className="recovery-hint">상담사 이름을 몰라도 센터를 먼저 선택하면 등록된 시연용 이름이 표시됩니다.</p>
                  {recoveryError && <p className="form-error" role="alert">{recoveryError}</p>}
                  <button type="submit" className="primary wide" disabled={recoveryLoading || !selectedCounselorId}>{recoveryLoading ? "불러오는 중…" : "아이디 확인"}</button>
                </form>
                {recoveredCounselor && (
                  <div className="recovery-results" aria-live="polite">
                    <strong>아이디 찾기 결과</strong>
                    <div>
                      <button type="button" onClick={() => useRecoveredUsername(recoveredCounselor.counselor_id)}>
                        <span><b>{recoveredCounselor.counselor_name}</b><small>{selectedRecoveryCenter ? `[${selectedRecoveryCenter.region_name}] ${selectedRecoveryCenter.center_name}` : ""}</small></span>
                        <code>{recoveredCounselor.counselor_id}</code>
                        <em>아이디 입력</em>
                      </button>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <>
                <h2 id="recovery-dialog-title">비밀번호 찾기</h2>
                <div className="demo-password-notice">
                  <span aria-hidden="true">✓</span>
                  <p>현재 사이트는 공개 시연용입니다.<br />모든 시연 계정의 비밀번호는 <code>demo</code>입니다.</p>
                </div>
                <button type="button" className="primary wide" onClick={useDemoPassword} autoFocus>비밀번호 입력란에 적용</button>
              </>
            )}
          </section>
        </div>
      )}
    </main>
  );
}
