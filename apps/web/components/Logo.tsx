// Logo mark from docs/design (two linked rings on petrol). Decorative: the wordmark next to it carries the name.
export function LogoMarke() {
  return (
    <svg width="30" height="30" viewBox="0 0 30 30" aria-hidden="true" className="shrink-0">
      <rect width="30" height="30" rx="8" fill="#0E5E5B" />
      <circle cx="10" cy="15" r="3.5" fill="none" stroke="#F5F3EC" strokeWidth="2" />
      <circle cx="20" cy="15" r="3.5" fill="none" stroke="#F5F3EC" strokeWidth="2" />
      <path d="M13.5 15h3" stroke="#F5F3EC" strokeWidth="2" />
    </svg>
  );
}
