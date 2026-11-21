const PATHS = {
  home: <path d="M3 10.2 12 3l9 7.2V21a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1V10.2Z" />,
  compass: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="m15.6 8.4-2 5.2-5.2 2 2-5.2 5.2-2Z" />
    </>
  ),
  plusSquare: (
    <>
      <rect x="3" y="3" width="18" height="18" rx="4" />
      <path d="M12 8v8M8 12h8" />
    </>
  ),
  heart: (
    <path d="M12 20.3s-7.5-4.6-9.3-9A5.1 5.1 0 0 1 12 6.5a5.1 5.1 0 0 1 9.3 4.8c-1.8 4.4-9.3 9-9.3 9Z" />
  ),
  user: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4.5 21a7.5 7.5 0 0 1 15 0" />
    </>
  ),
  link: (
    <>
      <path d="M10 13.8a4 4 0 0 0 5.7 0l2.6-2.6a4 4 0 0 0-5.7-5.7L11.4 6.7" />
      <path d="M14 10.2a4 4 0 0 0-5.7 0l-2.6 2.6a4 4 0 1 0 5.7 5.7l1.2-1.2" />
    </>
  ),
  pulse: <path d="M2 12h4l2.5-6 4 12 3-8 2 2h4.5" />,
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5M12 8h.01" />
    </>
  ),
  bookmark: <path d="M6 3.5h12v17l-6-4.2-6 4.2v-17Z" />,
  comment: <path d="M21 11.6a8.6 8.6 0 0 1-9 8.6 9.8 9.8 0 0 1-3.4-.6L3 21l1.5-4.3A8.4 8.4 0 0 1 3 11.6 8.6 8.6 0 0 1 12 3a8.6 8.6 0 0 1 9 8.6Z" />,
  share: (
    <>
      <path d="m22 2-7 20-4-9-9-4 20-7Z" />
      <path d="M22 2 11 13" />
    </>
  ),
  check: <path d="m4.5 12.5 5 5 10-11" />,
  alert: (
    <>
      <path d="M10.3 3.9 2.4 18a2 2 0 0 0 1.7 3h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" />
      <path d="M12 9v4M12 17h.01" />
    </>
  ),
  plus: <path d="M12 5v14M5 12h14" />,
  close: <path d="M6 6l12 12M18 6 6 18" />,
  arrow: (
    <>
      <path d="M5 12h14" />
      <path d="m13 6 6 6-6 6" />
    </>
  ),
  grid: (
    <>
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </>
  ),
  verified: (
    <>
      <path d="m12 2 2.4 1.8 3 .1.9 2.8 2.4 1.7-1 2.9 1 2.9-2.4 1.7-.9 2.8-3 .1L12 22l-2.4-1.8-3-.1-.9-2.8L3.3 15.6l1-2.9-1-2.9 2.4-1.7.9-2.8 3-.1L12 2Z" />
      <path d="m8.5 12.2 2.3 2.3 4.7-5" />
    </>
  ),
};

export default function Icons({ name, size = 24, className = '', fill = 'none' }) {
  const path = PATHS[name] || PATHS.info;
  return (
    <svg
      className={`icon ${className}`.trim()}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={fill}
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {path}
    </svg>
  );
}
