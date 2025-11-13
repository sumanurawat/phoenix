import type { Creation } from '../types/creation';

type FirestoreTimestamp = {
  _seconds?: number;
  _nanoseconds?: number;
  seconds?: number;
  nanoseconds?: number;
};

type NormalizationOptions = {
  fallbackUsername?: string;
  fallbackUserId?: string;
};

const toMilliseconds = (value: unknown): number | undefined => {
  if (!value) {
    return undefined;
  }

  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : undefined;
  }

  if (typeof value === 'string') {
    const parsed = Date.parse(value);
    return Number.isNaN(parsed) ? undefined : parsed;
  }

  if (typeof value === 'object') {
    const timestamp = value as FirestoreTimestamp;
    const seconds = timestamp._seconds ?? timestamp.seconds;
    const nanoseconds = timestamp._nanoseconds ?? timestamp.nanoseconds ?? 0;

    if (typeof seconds === 'number') {
      return seconds * 1000 + Math.round(nanoseconds / 1_000_000);
    }
  }

  return undefined;
};

const fallbackId = () => Math.random().toString(36).slice(2);

export const normalizeCreation = (
  rawCreation: Record<string, unknown>,
  options: NormalizationOptions = {}
): Creation => {
  const id = String(rawCreation.id ?? rawCreation.creationId ?? fallbackId());
  const username = String(rawCreation.username ?? options.fallbackUsername ?? 'unknown');
  const userId = String(rawCreation.userId ?? options.fallbackUserId ?? '');
  const mediaUrl = String(rawCreation.mediaUrl ?? '');
  const mediaType = (rawCreation.mediaType as Creation['mediaType']) ?? 'video';
  const status = (rawCreation.status as Creation['status']) ?? 'published';

  const createdAt = toMilliseconds(rawCreation.createdAt) ?? Date.now();
  const publishedAt = toMilliseconds(rawCreation.publishedAt);

  return {
    id,
    userId,
    username,
    mediaType,
    mediaUrl,
    thumbnailUrl: typeof rawCreation.thumbnailUrl === 'string' ? rawCreation.thumbnailUrl : undefined,
    prompt: typeof rawCreation.prompt === 'string' ? rawCreation.prompt : '',
    caption: typeof rawCreation.caption === 'string' ? rawCreation.caption : undefined,
    status,
    aspectRatio: typeof rawCreation.aspectRatio === 'string' ? rawCreation.aspectRatio : undefined,
    duration: typeof rawCreation.duration === 'number' ? rawCreation.duration : undefined,
    likeCount: typeof rawCreation.likeCount === 'number' ? rawCreation.likeCount : 0,
    commentCount: typeof rawCreation.commentCount === 'number' ? rawCreation.commentCount : 0,
    isLiked: typeof rawCreation.isLiked === 'boolean' ? rawCreation.isLiked : undefined,
    createdAt,
    publishedAt,
  };
};
