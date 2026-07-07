interface SpinnerProps {
  size?: number;
}

export default function Spinner({ size = 44 }: SpinnerProps) {
  return (
    <div
      className="animate-spin rounded-full border-[3px] border-[#e2e8f0] border-t-[#2563eb]"
      style={{ width: size, height: size }}
    />
  );
}
