import { Card } from "@hanzo/ui";

const ListSkeleton = () => {
  return (
    <div className="flex flex-row justify-between rounded-lg bg-background px-4 py-3">
      {/* left side */}
      <div className="flex min-w-0 items-center gap-4">
        {/* Icon skeleton */}
        <div className="flex h-[32px] w-[32px] items-center justify-center rounded-lg">
          
        </div>

        <div className="flex min-w-0 flex-col justify-start gap-[7px]">
          {/* Title and time skeleton */}
          <div className="flex min-w-0 items-baseline max-md:flex-col">
            
            
          </div>
          {/* Description skeleton */}
          
        </div>
      </div>

      {/* right side */}
      <div className="ml-5 flex items-center gap-2">
        
      </div>
    </div>
  );
};

export default ListSkeleton;
