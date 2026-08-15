import { test, expect } from '@playwright/test';

test.describe('Reserva Pública Móvil (Happy Path)', () => {
  test.use({ viewport: { width: 320, height: 600 } });

  test('completa el flujo de reserva pública en pantalla de 320px', async ({ page }) => {
    // 1. Navegar al wizard de reserva
    await page.goto('/reservar');

    // 2. Wizard Step 1: Servicio
    await expect(page.getByRole('heading', { name: '¿Qué quieres reservar?' })).toBeVisible({ timeout: 10000 });
    const serviceRadio = page.locator('input[name="service_selection"]').first();
    await serviceRadio.check();
    await page.getByRole('button', { name: 'Continuar' }).click();

    // 3. Step 2: Profesional
    await expect(page.getByRole('heading', { name: '¿Con quién prefieres atenderte?' })).toBeVisible({ timeout: 10000 });
    await page.locator('input[name="provider_selection"]').first().check();
    await page.getByRole('button', { name: 'Continuar' }).click();

    // 4. Step 3: Fecha y Horario
    await expect(page.getByRole('heading', { name: 'Elige una fecha y una hora' })).toBeVisible({ timeout: 10000 });
    const slotButtons = page.locator('button[data-starts-at]');
    await expect(slotButtons.first()).toBeVisible({ timeout: 10000 });
    await slotButtons.first().click();
    await page.getByRole('button', { name: 'Continuar' }).click();

    // 5. Step 4: Datos del cliente
    await expect(page.getByRole('heading', { name: 'Ingresa tus datos de contacto' })).toBeVisible({ timeout: 10000 });

    await page.locator('input[name="customer_name"]').fill('Juan Pérez E2E');
    await page.locator('input[name="customer_email"]').fill('juan.perez@estudionomada.cl');
    await page.locator('input[name="customer_phone"]').fill('+56912345678');
    await page.locator('textarea[name="customer_notes"]').fill('Nota de prueba E2E');

    // Confirmar la reserva
    await page.getByRole('button', { name: 'Confirmar reserva' }).click();

    // 6. Confirmación
    await expect(page).toHaveURL(/.*\/reservar\/confirmacion\/.+/, { timeout: 10000 });
    await expect(page.getByText('¡Reserva confirmada!')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Corte y Barba E2E')).toBeVisible();
  });
});
