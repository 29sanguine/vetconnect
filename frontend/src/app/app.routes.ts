import { Routes } from '@angular/router';
import { authGuard } from './guards/auth.guard';
import { BookingComponent } from './components/booking/booking.component';
import { LoginComponent } from './components/login/login.component';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'reservas', component: BookingComponent, canActivate: [authGuard], data: { role: 'TUTOR' } },
  { path: '', pathMatch: 'full', redirectTo: 'reservas' },
  { path: '**', redirectTo: 'reservas' },
];
