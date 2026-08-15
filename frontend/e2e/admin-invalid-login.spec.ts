import { test, expect } from '@playwright/test';

test.describe('Login Administrativo Inválido', () => {
  test('muestra mensaje genérico ante credenciales incorrectas sin filtrar existencia de cuenta', async ({ page }) => {
    await page.goto('/admin/login');
    await expect(page.getByRole('heading', { name: 'Panel de Administración' })).toBeVisible({ timeout: 10000 });

    await page.getByLabel('Correo electrónico').fill('desconocido@estudionomada.cl');
    await page.getByLabel('Contraseña').fill('ContrasenaErronea123!');
    await page.getByRole('button', { name: 'Iniciar sesión' }).click();

    // Mensaje genérico uniforme
    const errorAlert = page.getByText('Credenciales inválidas. Verifica tu correo y contraseña.');
    await expect(errorAlert).toBeVisible({ timeout: 10000 });

    // Foco restaurado al campo email
    await expect(page.getByLabel('Correo electrónico')).toBeFocused();
  });
});
