import { SignUp } from '@clerk/nextjs'

export default function SignUpPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[var(--off-white)]">
      <SignUp />
      <p style={{
        marginTop: '16px',
        fontFamily: 'var(--font-mono, monospace)',
        fontSize: '0.6rem',
        letterSpacing: '0.05em',
        color: '#9aab90',
        textAlign: 'center',
      }}>
        By signing up, you agree to our{' '}
        <a href="https://www.strwatch.io/terms.html" target="_blank" rel="noopener noreferrer" style={{ color: '#2d7a4f', textDecoration: 'underline', textUnderlineOffset: '2px' }}>
          Terms of Service
        </a>{' '}and{' '}
        <a href="https://www.strwatch.io/privacy.html" target="_blank" rel="noopener noreferrer" style={{ color: '#2d7a4f', textDecoration: 'underline', textUnderlineOffset: '2px' }}>
          Privacy Policy
        </a>.
      </p>
    </div>
  )
}
