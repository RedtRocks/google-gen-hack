import { Route, Switch } from "wouter";
import { LegalDocumentPage } from "@client/routes/LegalDocumentPage";
import { ResultsPage } from "@client/routes/ResultsPage";
import { NotFound } from "@client/routes/NotFound";
import { QueryClientProvider } from "@client/api";
import { ErrorBoundary } from "@client/components/ErrorBoundary";
import { Router } from "./components/Router/Router";
import { Toaster } from 'react-hot-toast';


export const App = () => {
  return (
    <QueryClientProvider>
      <Router>
        <ErrorBoundary>
          <Switch>
            <Route path="/" component={LegalDocumentPage} />
            <Route path="/results/:documentId" component={ResultsPage} />
            <Route component={NotFound} />
          </Switch>
        </ErrorBoundary>
      </Router>
      <Toaster 
        position="bottom-right"
      />
    </QueryClientProvider>
  );
};
