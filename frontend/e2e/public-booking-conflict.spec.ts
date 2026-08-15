import { test, expect } from '@playwright/test';
import { execSync } from 'child_process';

test.describe('Conflicto Concurrente Real de Reserva (409)', () => {
  test.use({ viewport: { width: 320, height: 600 } });

  test('detecta conflicto de horario, preserva datos del cliente y permite re-selección', async ({ page }) => {
    // 1. Navegar al wizard de reserva
    await page.goto('/reservar');

    // Step 1: Servicio
    await expect(page.getByRole('heading', { name: '¿Qué quieres reservar?' })).toBeVisible({ timeout: 10000 });
    await page.locator('input[name="service_selection"]').first().check();
    await page.getByRole('button', { name: 'Continuar' }).click();

    // 2. Step 2: Profesional
    await expect(page.getByRole('heading', { name: '¿Con quién prefieres atenderte?' })).toBeVisible({ timeout: 10000 });
    await page.locator('input[name="provider_selection"]').first().check();
    await page.getByRole('button', { name: 'Continuar' }).click();

    // 3. Step 3: Seleccionar un slot
    await expect(page.getByRole('heading', { name: 'Elige una fecha y una hora' })).toBeVisible({ timeout: 10000 });
    const slotButtons = page.locator('button[data-starts-at]');
    await expect(slotButtons.first()).toBeVisible({ timeout: 10000 });

    const slotCount = await slotButtons.count();
    const chosenSlot = slotCount > 1 ? slotButtons.nth(1) : slotButtons.first();
    const startsAt = await chosenSlot.getAttribute('data-starts-at');
    expect(startsAt).toBeTruthy();

    await chosenSlot.click();
    await page.getByRole('button', { name: 'Continuar' }).click();

    // 4. Step 4: Llenar datos de cliente
    await expect(page.getByRole('heading', { name: 'Ingresa tus datos de contacto' })).toBeVisible({ timeout: 10000 });
    await page.locator('input[name="customer_name"]').fill('Carlos Conflicto');
    await page.locator('input[name="customer_email"]').fill('carlos@estudionomada.cl');
    await page.locator('input[name="customer_phone"]').fill('+56987654321');

    // 5. Ocupar el slot en background mediante el helper de backend antes de confirmar
    const e2eDbUrl = process.env.E2E_DATABASE_URL || 'postgresql+psycopg://booking_e2e_user:booking_e2e_password@127.0.0.1:5434/booking_e2e';
    execSync(
      `cd ../backend && DATABASE_URL="${e2eDbUrl}" PYTHONPATH=. uv run python scripts/create_conflicting_booking.py --starts-at "${startsAt}"`,
      { stdio: 'inherit' }
    );

    // 6. Intentar confirmar la reserva
    await page.getByRole('button', { name: 'Confirmar reserva' }).click();

    // 7. Verificar que el wizard regresa al paso 3 y muestra la alerta focalizada
    await expect(page.getByRole('heading', { name: 'Elige una fecha y una hora' })).toBeVisible({ timeout: 10000 });
    const alert = page.getByText('Esa hora acaba de ser reservada. Actualizamos los horarios para que elijas otra.');
    await expect(alert).toBeVisible();

    // 8. Seleccionar otro slot disponible
    const newSlotButtons = page.locator('button[data-starts-at]');
    const newSlotCount = await newSlotButtons.count();
    const newSlot = newSlotCount > 2 ? newSlotButtons.nth(2) : newSlotButtons.last();
    await newSlot.click();
    await page.getByRole('button', { name: 'Continuar' }).click();

    // 9. Verificar que los datos del cliente fueron preservados
    await expect(page.locator('input[name="customer_name"]')).toHaveValue('Carlos Conflicto');
    await expect(page.locator('input[name="customer_email"]')).toHaveValue('carlos@estudionomada.cl');
    await expect(page.locator('input[name="customer_phone"]')).toHaveValue('+56987654321');

    // 10. Confirmar exitosamente
    await page.getByRole('button', { name: 'Confirmar reserva' }).click();
    await expect(page).toHaveURL(/.*\/reservar\/confirmacion\/.+/, { timeout: 10000 });
    await expect(page.getByText('¡Reserva confirmada!')).toBeVisible({ timeout: 10000 });
  });
});
