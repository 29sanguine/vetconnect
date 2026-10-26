import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { API_URL } from '../api.config';

export interface Doctor {
  id: number;
  full_name: string;
  specialty: string;
  box_number: number;
}

export interface Slot {
  start_time: string; // "2026-10-22T09:00:00" (hora local de la clínica)
  end_time: string;
}

export interface Appointment {
  id: number;
  doctor_id: number;
  tutor_id: number;
  status: 'CONFIRMED' | 'CANCELLED';
  start_time: string;
  end_time: string;
}

@Injectable({ providedIn: 'root' })
export class AppointmentService {
  private http = inject(HttpClient);

  getDoctors(): Observable<Doctor[]> {
    return this.http.get<Doctor[]>(`${API_URL}/doctors`);
  }

  getAvailableSlots(doctorId: number, date: string): Observable<Slot[]> {
    const params = new HttpParams().set('doctor_id', doctorId).set('date', date);
    return this.http.get<Slot[]>(`${API_URL}/appointments/available-slots`, { params });
  }

  reserve(doctorId: number, slot: Slot): Observable<Appointment> {
    return this.http.post<Appointment>(`${API_URL}/appointments/reserve`, {
      doctor_id: doctorId,
      start_time: slot.start_time,
      end_time: slot.end_time,
    });
  }
}
