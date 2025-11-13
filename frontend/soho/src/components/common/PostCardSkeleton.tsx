export const PostCardSkeleton = () => {
  return (
    <article className="bg-momo-gray-800 rounded-xl overflow-hidden shadow-lg">
      {/* Header Skeleton */}
      <div className="flex items-center gap-3 p-4 animate-pulse">
        <div className="w-10 h-10 rounded-full bg-momo-gray-700"></div>
        <div className="h-4 bg-momo-gray-700 rounded w-24"></div>
      </div>

      {/* Media Skeleton */}
      <div className="bg-momo-gray-700 aspect-square animate-pulse"></div>

      {/* Actions Skeleton */}
      <div className="p-4 space-y-3">
        <div className="flex items-center gap-4 animate-pulse">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded bg-momo-gray-700"></div>
            <div className="h-4 w-8 bg-momo-gray-700 rounded"></div>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded bg-momo-gray-700"></div>
            <div className="h-4 w-8 bg-momo-gray-700 rounded"></div>
          </div>
        </div>

        {/* Caption Skeleton */}
        <div className="space-y-2 animate-pulse">
          <div className="h-3 bg-momo-gray-700 rounded w-3/4"></div>
          <div className="h-3 bg-momo-gray-700 rounded w-1/2"></div>
        </div>
      </div>
    </article>
  );
};
