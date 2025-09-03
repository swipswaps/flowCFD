export function formatTime(seconds: number): string {
  if (isNaN(seconds) || seconds < 0) {
    return "00:00:00";
  }
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  const ms = Math.floor((seconds * 1000) % 1000);

  const pad = (num: number) => num.toString().padStart(2, '0');
  const padMs = (num: number) => num.toString().padStart(3, '0');

  return `${pad(hours)}:${pad(minutes)}:${pad(remainingSeconds)}.${padMs(ms)}`;
}