import { Route, Switch } from "wouter";
import { LegalDocumentPage } from "@client/routes/LegalDocumentPage";
import { ResultsPage } from "@client/routes/ResultsPage";
import { NotFound } from "@client/routes/NotFound";
import { Toaster } from 'react-hot-toast';


export const App = () => {
  return (
    <>
      <Switch>
        <Route path="/" component={LegalDocumentPage} />
        <Route path="/results/:documentId" component={ResultsPage} />
        <Route component={NotFound} />
      </Switch>
      <Toaster 
        position="bottom-right"
      />
    </>
  );
};
