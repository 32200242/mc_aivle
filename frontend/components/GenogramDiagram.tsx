"use client";

type Gender = "male" | "female" | "unknown";

type FamilyMember = {
  id: string;
  label: string;
  detail: string;
  gender: Gender;
};

type GenogramDiagramProps = {
  clientName?: string;
  clientGender?: string;
  familyText?: string;
  onChange: (value: string) => void;
};

const MAX_VISIBLE_CHILDREN = 5;


export default function GenogramDiagram({ clientName = "", clientGender = "", familyText = "", onChange }: GenogramDiagramProps) {
  const structure = parseFamilyStructure(clientName, clientGender, familyText);
  const primaryX = structure.spouse ? 230 : 320;
  const spouseX = 410;
  const coupleCenterX = structure.spouse ? (primaryX + spouseX) / 2 : primaryX;
  const childXs = distributeChildren(structure.children.length);

  return <div className="genogram-field" data-genogram-ready="true">
    <div className="genogram-canvas">
      <svg className="genogram-svg" viewBox="0 0 640 260" role="img" aria-labelledby="genogram-title genogram-description">
        <title id="genogram-title">{structure.primary.label} 가족 가계도</title>
        <desc id="genogram-description">확인된 가족관계 정보만 반영한 가계도입니다.</desc>

        {structure.spouse && <line className="genogram-line" x1={primaryX + 25} y1="58" x2={spouseX - 25} y2="58" />}
        {structure.children.length > 0 && <>
          <line className="genogram-line" x1={coupleCenterX} y1="58" x2={coupleCenterX} y2="128" />
          {structure.children.length > 1 && <line className="genogram-line" x1={childXs[0]} y1="128" x2={childXs.at(-1)} y2="128" />}
          {childXs.map((x, index) => <line className="genogram-line" x1={x} y1="128" x2={x} y2="164" key={`child-line-${index}`} />)}
        </>}

        <PersonNode member={structure.primary} x={primaryX} y={58} primary />
        {structure.spouse && <PersonNode member={structure.spouse} x={spouseX} y={58} />}
        {structure.children.map((child, index) => <PersonNode member={child} x={childXs[index]} y={188} key={child.id} />)}
      </svg>
      <p className="genogram-official-note">※ 작성법과 예시(부록)</p>
      {structure.children.length === 0 && !structure.spouse && <p className="genogram-empty-note screen-only-form-guidance">확인된 가족관계를 아래에 입력하면 가계도에 자동 반영됩니다.</p>}
    </div>
    <div className="genogram-legend screen-only-form-guidance" aria-label="가계도 기호 안내">
      <span><i className="legend-square"/> 남</span><span><i className="legend-circle"/> 여</span><span><i className="legend-diamond"/> 성별 미확인</span><span><i className="legend-double"/> 내담자</span>
    </div>
    <label className="genogram-source-label">
      <span>가족관계 참고사항</span>
      <textarea value={familyText} onChange={event => onChange(event.target.value)} rows={4} placeholder="예: 배우자(35세), 자녀 1명과 동거" />
    </label>
  </div>;
}


function parseFamilyStructure(clientName: string, clientGender: string, familyText: string) {
  const normalized = familyText.replace(/\s+/g, " ").trim();
  const spouseRole = normalized.match(/배우자|남편|아내/)?.[0];
  const spouseAge = spouseRole
    ? normalized.match(new RegExp(`${spouseRole}[^0-9]{0,6}(\\d{1,3})\\s*세`))?.[1]
    : undefined;
  const spouse = spouseRole ? {
    id: "spouse",
    label: spouseRole,
    detail: spouseAge ? `${spouseAge}세` : "",
    gender: spouseRole === "남편" ? "male" as const : spouseRole === "아내" ? "female" as const : "unknown" as const,
  } : null;

  const explicitlyGenderedChildren: FamilyMember[] = [];
  for (const match of normalized.matchAll(/(아들|딸)\s*(\d{1,2})?\s*명?/g)) {
    const count = Math.max(1, Math.min(Number(match[2] || 1), MAX_VISIBLE_CHILDREN));
    for (let index = 0; index < count; index += 1) {
      explicitlyGenderedChildren.push({
        id: `${match[1]}-${explicitlyGenderedChildren.length + 1}`,
        label: count > 1 ? `${match[1]} ${index + 1}` : match[1],
        detail: "",
        gender: match[1] === "아들" ? "male" : "female",
      });
    }
  }

  const statedChildCount = Number(normalized.match(/자녀\s*(\d{1,2})\s*명/)?.[1] || 0);
  const inferredChildCount = statedChildCount || explicitlyGenderedChildren.length || (normalized.includes("자녀") ? 1 : 0);
  const children: FamilyMember[] = explicitlyGenderedChildren.slice(0, MAX_VISIBLE_CHILDREN);
  const visibleCount = Math.min(inferredChildCount, MAX_VISIBLE_CHILDREN);
  while (children.length < visibleCount) {
    const childNumber = children.length + 1;
    const hiddenCount = inferredChildCount > MAX_VISIBLE_CHILDREN && childNumber === MAX_VISIBLE_CHILDREN
      ? inferredChildCount - MAX_VISIBLE_CHILDREN + 1
      : 0;
    children.push({
      id: `child-${childNumber}`,
      label: hiddenCount ? `자녀 외 ${hiddenCount}명` : inferredChildCount === 1 ? "자녀" : `자녀 ${childNumber}`,
      detail: "",
      gender: "unknown",
    });
  }

  return {
    primary: {
      id: "primary",
      label: clientName.trim() || "내담자",
      detail: "본인",
      gender: toGender(clientGender),
    } satisfies FamilyMember,
    spouse,
    children,
  };
}


function toGender(value: string): Gender {
  const normalized = value.trim();
  if (normalized.startsWith("남")) return "male";
  if (normalized.startsWith("여")) return "female";
  return "unknown";
}


function distributeChildren(count: number): number[] {
  if (count <= 0) return [];
  if (count === 1) return [320];
  const start = 135;
  const end = 505;
  return Array.from({ length: count }, (_, index) => start + ((end - start) * index) / (count - 1));
}


function PersonNode({ member, x, y, primary = false }: { member: FamilyMember; x: number; y: number; primary?: boolean }) {
  const label = member.label.length > 10 ? `${member.label.slice(0, 9)}…` : member.label;
  return <g className={`genogram-person ${primary ? "primary" : ""}`} transform={`translate(${x} ${y})`}>
    {member.gender === "male" && <>
      {primary && <rect className="genogram-primary-outline" x="-25" y="-25" width="50" height="50" rx="2" />}
      <rect className="genogram-node-shape" x="-20" y="-20" width="40" height="40" rx="1" />
    </>}
    {member.gender === "female" && <>
      {primary && <circle className="genogram-primary-outline" cx="0" cy="0" r="25" />}
      <circle className="genogram-node-shape" cx="0" cy="0" r="20" />
    </>}
    {member.gender === "unknown" && <>
      {primary && <polygon className="genogram-primary-outline" points="0,-28 28,0 0,28 -28,0" />}
      <polygon className="genogram-node-shape" points="0,-22 22,0 0,22 -22,0" />
    </>}
    <text className="genogram-person-label" x="0" y="39" textAnchor="middle">{label}</text>
    {member.detail && <text className="genogram-person-detail" x="0" y="55" textAnchor="middle">{member.detail}</text>}
  </g>;
}
