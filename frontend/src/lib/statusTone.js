/** Maps an order or trade status string onto a semantic badge tone. */
export function statusTone(status) {
  switch (String(status ?? '').toUpperCase()) {
    case 'FILLED':
      return 'profit';
    case 'REJECTED':
      return 'loss';
    case 'PENDING':
    case 'PARTIAL':
      return 'warning';
    case 'CANCELLED':
      return 'neutral';
    default:
      return 'neutral';
  }
}

export default statusTone;
