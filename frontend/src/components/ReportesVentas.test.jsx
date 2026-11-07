import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { reportesApi } from "../api";
import ReportesVentas from "./ReportesVentas";
vi.mock("../api",()=>({getRol:()=> "administrador",reportesApi:{ventas:vi.fn(),historial:vi.fn(),generar:vi.fn(),descargar:vi.fn(),conciliacion:vi.fn()}}));
const datos={cantidad_pagos:1,total_ventas:"7.00",total_reembolsos:"0.00",total_neto:"7.00",por_metodo:{efectivo:{cantidad:1,ventas:"7.00",reembolsos:"0.00",neto:"7.00"},qr:{cantidad:0,ventas:"0.00",reembolsos:"0.00",neto:"0.00"}},productos:[],categorias:[]};
beforeEach(()=>{vi.clearAllMocks();reportesApi.historial.mockResolvedValue([]);reportesApi.ventas.mockResolvedValue(datos);reportesApi.generar.mockResolvedValue({id:8});reportesApi.descargar.mockResolvedValue();});
describe("Reportes PDF e historial",()=>{
 it("consulta ventas y separa métodos",async()=>{render(<ReportesVentas/>);fireEvent.click(screen.getByRole("button",{name:"Consultar período"}));expect(await screen.findByText("Yape · QR")).toBeInTheDocument();expect(screen.getByText("Ventas brutas")).toBeInTheDocument();});
 it("genera y descarga PDF de ventas",async()=>{render(<ReportesVentas/>);fireEvent.click(screen.getByRole("button",{name:"Descargar ventas PDF"}));await waitFor(()=>expect(reportesApi.generar).toHaveBeenCalledWith(expect.objectContaining({tipo:"VENTAS"})));await waitFor(()=>expect(reportesApi.descargar).toHaveBeenCalledWith(8));expect(await screen.findByRole("status")).toHaveTextContent("guardado en el historial");});
 it("genera reporte de reportes PDF",async()=>{render(<ReportesVentas/>);fireEvent.click(screen.getByRole("button",{name:"Reporte de reportes PDF"}));await waitFor(()=>expect(reportesApi.generar).toHaveBeenCalledWith(expect.objectContaining({tipo:"HISTORIAL"})));});
 it("muestra errores de generación",async()=>{reportesApi.generar.mockRejectedValue(new Error("No se pudo generar el PDF"));render(<ReportesVentas/>);fireEvent.click(screen.getByRole("button",{name:"Descargar ventas PDF"}));expect(await screen.findByRole("alert")).toHaveTextContent("No se pudo generar");expect(reportesApi.descargar).not.toHaveBeenCalled();});
});
