import express from 'express';
import type {Application, Request, Response} from 'express';
import 'dotenv/config';
import authRouter from './auth/routes.js';
import organizationRouter from './organization/routes.js';

const app: Application = express();
const PORT = Number(process.env.SERVER_PORT ?? 3000);
const frontendOrigin = process.env.FRONTEND_ORIGIN ?? 'http://localhost:8080';

app.disable('x-powered-by');
app.use((request, response, next) => {
    response.setHeader('Access-Control-Allow-Origin', frontendOrigin);
    response.setHeader('Access-Control-Allow-Credentials', 'true');
    response.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-CSRF-Token');
    response.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    if (request.method === 'OPTIONS') {
        response.status(204).end();
        return;
    }
    next();
});
app.use(express.json({limit: '1mb'}));
app.use(express.urlencoded({extended: false}));
app.get('/health', (_request: Request, response: Response) => {
    response.json({ok: true});
});
app.use(authRouter);
app.use(organizationRouter);

app.use((error: unknown, _request: Request, response: Response, _next: unknown) => {
    const status = error instanceof Error && 'status' in error
        ? Number((error as Error & {status: number}).status)
        : 500;
    const safeStatus = [400, 401, 403, 404, 409].includes(status) ? status : 500;
    if (safeStatus === 500) console.error('[server] request failed', error);
    response.status(safeStatus).json({error: safeStatus === 500 ? 'internal_server_error' : error instanceof Error ? error.message : 'request_failed'});
});

app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});
