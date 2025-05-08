// Imports
import Alpine from "alpinejs";
import LoadLayout from "./modules/dashboard/LoadLayout";
import ModalDialog from "./modules/dashboard/ModalDialog";
import Tables from "./modules/dashboard/Tables";
import Tooltip from "./modules/dashboard/Tooltip";
import Generic from "./modules/dashboard/Generic";
import ResizeInput from "./modules/dashboard/ResizeInput";
import Inputs from "./modules/dashboard/Inputs";
import ImageSelect from "./modules/dashboard/ImageSelect";
import ImageUpload from "./modules/dashboard/ImageUpload";
import Calendar from "./modules/dashboard/Calendar";
import Specifics from "./modules/dashboard/Specifics";
import Tabs from "./modules/dashboard/Tabs";
import Recruitment from "./modules/dashboard/Recruitment";
import Kanban from "./modules/dashboard/Kanban";
import Chat from "./modules/dashboard/Chat";
import Dashboard from "./modules/dashboard/Dashboard";
import Helpdesk from "./modules/dashboard/Helpdesk";
import Faq from "./modules/dashboard/Faq";
import OrgChart from "./modules/dashboard/OrgChart";
// import Accordion from "./modules/dashboard/Accordion";
// import WorkEntry from "./modules/dashboard/WorkEntry";

// Instantiate a new objects
window.Alpine = Alpine;
Alpine.start();

const loadLayout = new LoadLayout();
// const tables = new Tables();
const modalDialog = new ModalDialog();
const tooltip = new Tooltip();
const generic = new Generic();
const resizeInput = new ResizeInput();
const inputs = new Inputs();
const imageSelect = new ImageSelect();
const imageUpload = new ImageUpload();
const calendar = new Calendar();
const specifics = new Specifics();
const tabs = new Tabs();
const recruitment = new Recruitment();
const kanban = new Kanban();
const chat = new Chat();
const dashbaord = new Dashboard();
const helpdesk = new Helpdesk();
const faq = new Faq();
const orgChart = new OrgChart();
const accordion = new Accordion();
// const workEntry = new WorkEntry();
