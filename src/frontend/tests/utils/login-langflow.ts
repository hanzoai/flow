import type { Page } from "@playwright/test";

export const loginFlow = async (page: Page) => {
  await page.goto("/");
  await page.getByPlaceholder("Username").fill("flow");
  await page.getByPlaceholder("Password").fill("flow");
  await page.getByRole("button", { name: "Sign In" }).click();
};
