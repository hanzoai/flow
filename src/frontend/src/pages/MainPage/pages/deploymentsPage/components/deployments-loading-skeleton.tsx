
const SKELETON_ROWS = 3;
const COLUMN_HEADERS = [
  "Name",
  "Type",
  "Status",
  "Health",
  "Attached",
  "Provider",
  "Last Modified",
  "Test",
  "",
];

export default function DeploymentsLoadingSkeleton() {
  return (
    <>
      <>
        <>
          {COLUMN_HEADERS.map((header) => (
            <>{header}</>
          ))}
        </>
      </>
      <>
        {Array.from({ length: SKELETON_ROWS }).map((_, i) => (
          <>
            <>
              <div className="flex flex-col gap-2">
                
                
              </div>
            </>
            <>
              
            </>
            <>
              
            </>
            <>
              <div className="flex items-center gap-2">
                
                
              </div>
            </>
            <>
              
            </>
            <>
              
            </>
            <>
              <div className="flex flex-col gap-2">
                
                
              </div>
            </>
            <>
              
            </>
            <>
              
            </>
          </>
        ))}
      </>
    </>
  );
}
