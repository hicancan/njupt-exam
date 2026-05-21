interface LogoProps {
    size?: 'small' | 'large';
    className?: string;
}

export function Logo({ size = 'small', className = '' }: LogoProps) {
    const isLarge = size === 'large';
    
    const containerClasses = isLarge 
        ? "text-6xl sm:text-[5.5rem] font-bold mb-8 tracking-tighter select-none"
        : "font-bold text-3xl tracking-tighter";
        
    const letterSpacing = isLarge ? '-3px' : '-1px';

    return (
        <div className={`${containerClasses} ${className}`} style={{ letterSpacing }}>
            <span style={{ color: '#4285F4' }}>N</span>
            <span style={{ color: '#EA4335' }}>J</span>
            <span style={{ color: '#FBBC05' }}>U</span>
            <span style={{ color: '#4285F4' }}>P</span>
            <span style={{ color: '#34A853' }}>T</span>
        </div>
    );
}
