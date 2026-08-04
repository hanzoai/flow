import { Textarea } from "@hanzo/ui";

export default function ErrorOutput({ value }: { value: string }) {
  return (
    <Textarea
      className={`h-full w-full text-destructive custom-scroll`}
      placeholder={"Empty"}
      value={value}
      readOnly
    />
  );
}
