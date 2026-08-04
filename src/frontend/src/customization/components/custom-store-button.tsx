import ForwardedIconComponent from "@/components/common/genericIconComponent";

export const CustomStoreButton = () => {
  return (
    <>
      <div className="flex w-full items-center" data-testid="button-store">
        <>
          <ForwardedIconComponent name="Store" className="h-4 w-4" />
          Store
        </>
      </div>
    </>
  );
};
