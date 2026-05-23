const { test, expect } = require('@playwright/test');

test('Product navigation flow', async ({ page }) => {
  // action1 — click
  await page.getByText('See How It Works').click();

  // action2 — click
  await page.getByText('Read details').click();

  // action3 — expandDropDown
  await page.getByRole('button', { name: 'Product' }).click();

  // action4 — click
  await page.getByText('Mix and Build').click();
});
