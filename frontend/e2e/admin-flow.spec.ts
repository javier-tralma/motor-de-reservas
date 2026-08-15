import { test, expect } from '@playwright/test';
import { execSync } from 'child_process';

test.describe('Flujo Administrativo Operativo', () => {
  test('inicia sesión, visualiza detalle de reserva y ejecuta transición a cancelada', async ({ page }) => {
    // 1. Crear una reserva aislada para la prueba administrativa
    const e2eDbUrl = process.env.E2E_DATABASE_URL || 'postgresql+psycopg://booking_e2e_user:booking_e2e_password@127.0.0.1:5434/booking_e2e';
    const output = execSync(
      `cd ../backend && DATABASE_URL="${e2eDbUrl}" PYTHONPATH=. uv run python scripts/create_admin_booking_for_test.py --name "Cliente Admin E2E" --email "adminclient@estudionomada.cl"`,
      { encoding: 'utf-8' }
    );
    const match = output.match(/BOOKING_DATE=(\d{4}-\d{2}-\d{2})/);
    const bookingDate = match ? match[1] : '';

    // 2. Navegar a Login
    await page.goto('/admin/login');
    await expect(page.getByRole('heading', { name: 'Panel de Administración' })).toBeVisible({ timeout: 10000 });

    await page.getByLabel('Correo electrónico').fill('admin@estudionomada.cl');
    await page.getByLabel('Contraseña').fill('AdminE2E2026!');
    await page.getByRole('button', { name: 'Iniciar sesión' }).click();

    // 3. Esperar autenticación y navegación al panel administrativo
    const reservasNavLink = page.getByRole('link', { name: 'Reservas' });
    await expect(reservasNavLink).toBeVisible({ timeout: 10000 });

    // 4. Navegar a la lista de reservas para la fecha de la cita
    await page.goto(`/admin/reservas?date=${bookingDate}`);
    await expect(page.getByRole('heading', { name: 'Reservas' })).toBeVisible({ timeout: 10000 });

    // 5. Buscar la reserva creada y hacer click en Ver detalle
    const bookingCell = page.getByRole('cell', { name: 'Cliente Admin E2E' });
    await expect(bookingCell).toBeVisible({ timeout: 10000 });

    const detailLink = page.getByRole('link', { name: 'Ver detalle' }).first();
    await detailLink.click();

    // 6. En la página de detalle, verificar carga y datos
    await expect(page.getByRole('heading', { name: 'Información del Cliente' })).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Cliente Admin E2E').first()).toBeVisible({ timeout: 10000 });

    // 7. Cancelar la reserva
    const cancelBtn = page.getByRole('button', { name: 'Cancelar Reserva' });
    await expect(cancelBtn).toBeVisible();
    await cancelBtn.click();

    // Modal de confirmación
    const confirmDialog = page.getByRole('dialog');
    await expect(confirmDialog).toBeVisible();
    await confirmDialog.getByRole('button', { name: 'Cancelar Reserva' }).click();

    // 8. Verificar que el estado cambió visualmente a Cancelada
    await expect(page.getByText('Cancelada').first()).toBeVisible({ timeout: 10000 });
  });
});
