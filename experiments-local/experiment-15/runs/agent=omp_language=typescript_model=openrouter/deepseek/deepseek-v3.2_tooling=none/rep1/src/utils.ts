export function parseId(idParam: unknown): number | null {
  if (typeof idParam === 'string') {
    const id = parseInt(idParam, 10);
    return isNaN(id) || id <= 0 ? null : id;
  }
  return null;
}

export function getStringParam(param: unknown): string | undefined {
  if (typeof param === 'string') {
    return param;
  }
  if (Array.isArray(param) && param.length > 0 && typeof param[0] === 'string') {
    return param[0];
  }
  return undefined;
}