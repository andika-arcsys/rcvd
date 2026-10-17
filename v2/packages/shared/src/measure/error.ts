export class MeasureError extends Error {
  readonly code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = 'MeasureError';
    this.code = code;
  }
}
