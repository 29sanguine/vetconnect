import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

/** Exige sesión válida y, si la ruta define data.role, que coincida. */
export const authGuard: CanActivateFn = (route) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const requiredRole = route.data?.['role'] as string | undefined;

  if (!auth.isLoggedIn()) return router.createUrlTree(['/login']);
  if (requiredRole && auth.getRole() !== requiredRole) {
    auth.logout();
    return router.createUrlTree(['/login']);
  }
  return true;
};
