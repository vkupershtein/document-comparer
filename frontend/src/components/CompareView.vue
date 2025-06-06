<template>
  <Toast />
  <div class="max-w-screen-xl mx-auto">    
    <h1 class="text-2xl font-bold mb-6 ml-4">Doc Comparison Tool</h1>
    <form class="flex flex-col gap-2 justify-center items-start w-md min-w-full max-w-md mt-4 mb-4 ml-4" @submit.prevent="submitFiles">
      <div class="flex">
        <FileUpload class="p-1 cursor-pointer" mode="basic" custom-upload  @select="handleFileUpload($event, 'left')" accept=".pdf,.xlsx" required />
        <Button v-if="leftFile?.type === 'application/pdf'" v-tooltip.top="'Truncate repeated headers and footers'" class=".w-32 ml-2" label="Crop Page" @click="leftPreviewVisible = true" />
      </div>
      <Select v-if="leftHeaders.length" v-model="leftTextColumn" :options="leftHeaders" placeholder="Left: Select Text Column" class="mb-2" />
      <Select v-if="leftHeaders.length" v-model="leftIdColumn" :options="leftHeaders" placeholder="Left: Select ID Column (optional)" class="mb-2" />  
      <div class="flex">
        <FileUpload class="p-1 cursor-pointer" mode="basic" custom-upload  @select="handleFileUpload($event, 'right')" accept=".pdf,.xlsx" required />
        <Button v-if="rightFile?.type === 'application/pdf'" v-tooltip.top="'Truncate repeated headers and footers'" class=".w-32 ml-2" label="Crop Page" @click="rightPreviewVisible = true" />
      </div>      
      <Select v-if="rightHeaders.length" v-model="rightTextColumn" :options="rightHeaders" placeholder="Left: Select Text Column" class="mb-2" />
      <Select v-if="rightHeaders.length" v-model="rightIdColumn" :options="rightHeaders" placeholder="Left: Select ID Column (optional)" class="mb-2" />     
      <Button class="w-50" label="Compare" severity="contrast" type="submit" />
    </form>

    <Dialog v-model:visible="loading" modal header="Comparison in Progress" :style="{ width: '40rem' }">
      <span class="text-surface-500 dark:text-surface-400 block mb-8 capitalize"> {{ taskStatus }}</span>
      <ProgressBar :value="taskProgress" style="height: 20px;" class="mx-4 my-4"/>
    </Dialog>    

    <DataTable v-if="comparisonResults.length > 0" 
      :value="comparisonResults"
      v-model:filters="filters"
      filterDisplay="row"
      :globalFilterFields="['text_left', 'text_right']"       
      paginator 
      :rows="100" 
      scrollable 
      scrollHeight="600px"
      showGridlines
      tableStyle="min-width: 50rem">
      <template #header>
        <div class="flex justify-between items-center">
          <div class="flex justify-start gap-2">
            <Button label="Export to Excel" severity="info" class="mr-3" @click="exportToExcel" />
            <Button label="Export to HTML" severity="info" class="mr-3" @click="exportToHTML" />
          </div>
          <div class="flex justify-start gap-2">
            <Button label="Clear Filters" severity="secondary" @click="filters = getDefaultFilters()" />
            <span class="p-input-icon-left">
              <i class="pi pi-search" />
              <InputText type="text" v-model="filters.global.value" placeholder="Search..." />
            </span>
          </div>
        </div>

      </template>
      <Column 
        field="type" 
        header="Type" 
        frozen 
      >
        <template #body="{ data }">
          <span class="capitalize">{{ data.type }}</span>
        </template>
        <template #filter="{ filterModel, filterCallback }">
          <Select
            v-model="filterModel.value"
            @change="filterCallback()"
            :options="['equal', 'changed', 'new', 'removed']"
            placeholder="Change type"
            class="p-column-filter"
            style="width: 100%"
          />
        </template>    
      </Column>
      <Column field="ratio" header="Similarity Ratio" frozen />
      <Column header="Original Text" style="max-width: 500px; min-width: 400px">
        <template #body="slotProps">
          <FormattedText :text="slotProps.data.text_left_report" />
        </template>
      </Column> 
      <Column header="Updated Text" style="max-width: 500px; min-width: 400px">
        <template #body="slotProps">
          <FormattedText :text="slotProps.data.text_right_report" />
        </template>
      </Column>
      <Column v-if='leftIdColumn' field="text_left_id" header="ID # Original" />
      <Column v-if='rightIdColumn' field="text_right_id" header="ID # Updated" />
      <Column field="page_number_left" header="Page Number # Original" />
      <Column field="page_number_right" header="Page Number # Updated" />        
    </DataTable>
  </div>
  <Dialog v-model:visible="leftPreviewVisible" modal>
    <PdfPreview v-if="leftFile?.type === 'application/pdf'" v-model:header-crop="leftHeaderCrop" v-model:footer-crop="leftFooterCrop" :file="leftFile" />
  </Dialog>
  <Dialog v-model:visible="rightPreviewVisible" modal>
    <PdfPreview v-if="rightFile?.type === 'application/pdf'" v-model:header-crop="rightHeaderCrop" v-model:footer-crop="rightFooterCrop" :file="rightFile" />
  </Dialog>  
</template>
  
<script setup>
  import { ref, onBeforeUnmount } from 'vue';
  import { FilterMatchMode } from '@primevue/core/api'
  import PdfPreview from '../components/PdfPreview.vue';
  import axios from 'axios';
  import ProgressSpinner from 'primevue/progressspinner';
  import Toast from 'primevue/toast';
  import DataTable from 'primevue/datatable';
  import Column from 'primevue/column';
  import Button from 'primevue/button';  
  import InputText from 'primevue/inputtext';
  import FileUpload from 'primevue/fileupload';
  import Dialog from 'primevue/dialog';
  import ProgressBar from 'primevue/progressbar';
  import { Select } from 'primevue';
  import { useToast } from 'primevue/usetoast';
  import FormattedText from '../components/FormattedText.vue';
  import * as XLSX from 'xlsx'; 

  const taskId = ref(null);
  const taskProgress = ref(0);
  const taskStatus = ref('')
  const pollingInterval = ref(null); 

  const leftFile = ref(null);
  const rightFile = ref(null);
  const leftHeaders = ref([]);
  const rightHeaders = ref([]);
  const loading = ref(false);
  const comparisonResults = ref([]);
  const leftTextColumn = ref('');
  const rightTextColumn = ref('');
  const leftIdColumn = ref('');
  const rightIdColumn = ref('');

  const leftPreviewVisible = ref(false)
  const rightPreviewVisible = ref(false)

  const leftHeaderCrop = ref(50);
  const leftFooterCrop = ref(50);
  const rightHeaderCrop = ref(50);
  const rightFooterCrop = ref(50);

  onBeforeUnmount(() => {
    if (pollingInterval.value) {
      clearInterval(pollingInterval.value);
    }
  });

  const toast = useToast();

  const getDefaultFilters = () => ({
    global: { value: null, matchMode: FilterMatchMode.CONTAINS },
    type: { value: null, matchMode: FilterMatchMode.EQUALS }
  })

  const filters = ref(getDefaultFilters())

  const parseExcelHeaders = async (file) => {
    const arrayBuffer = await file.arrayBuffer();
    const workbook = XLSX.read(arrayBuffer, { type: 'array' });
    const sheet = workbook.Sheets[workbook.SheetNames[0]];
    const data = XLSX.utils.sheet_to_json(sheet, { header: 1 });
    return data[0] || [];
  };

  const handleFileUpload = async (event, side) => {
    const file = event.files[0];
    const allowedTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.ms-excel'
    ];    
    if (!allowedTypes.includes(file.type)) {
      toast.add({ severity: 'warn', summary: 'Invalid File Type', detail: 'Only PDF or Excel files are supported.', life: 3000 });
      return;
    }    
    if (side === 'left') {
      leftFile.value = file;
      if (file.name.endsWith('.xlsx')) { 
        leftHeaders.value = await parseExcelHeaders(file); 
      } else leftHeaders.value = []; 
    }
    else {
      rightFile.value = file;
      if (file.name.endsWith('.xlsx')) { 
        rightHeaders.value = await parseExcelHeaders(file); 
      } else rightHeaders.value = [];
    }
  };

  
  const submitFiles = async () => {
    if (!leftFile.value || !rightFile.value) {
      toast.add({ severity: 'error', summary: 'File is not uploaded', detail: 'Please select both files', life: 3000 });
      return;
    }

    if ((leftHeaders.value.length > 0 && !leftTextColumn.value) || (rightHeaders.value.length > 0 && !rightTextColumn.value)) {
      toast.add({ severity: 'error', summary: 'Text column not present', detail: 'For Excel file text column must be selected', life: 3000 });
      return;      
    }

    taskStatus.value = "Wait..."
    loading.value = true;
    
    const formData = new FormData()
    formData.append('left_file', leftFile.value)
    formData.append('right_file', rightFile.value)

    formData.append('header_left', leftHeaderCrop.value ?? 50);
    formData.append('footer_left', leftFooterCrop.value ?? 50);
    formData.append('size_weight_left', 0.8)
    formData.append('header_right', rightHeaderCrop.value ?? 50);
    formData.append('footer_right', rightFooterCrop.value ?? 50);
    formData.append('size_weight_right', 0.8)
    formData.append('ratio_threshold', 0.7)
    formData.append('length_threshold', 30)

    formData.append('text_column_left', leftTextColumn.value)
    formData.append('id_column_left', leftIdColumn.value)
    formData.append('text_column_right', rightTextColumn.value)
    formData.append('id_column_right', rightIdColumn.value)   

    try {
      const response = await axios.post(`${import.meta.env.VITE_API_BASE_URL}/start-task/`, formData);
      taskId.value = response.data.task_id;
      startPolling();
    } catch (error) {
      console.error('Error uploading files:', error);
      toast.add({ severity: 'error', summary: 'Processing error', detail: 'Error occured while making comparison report', life: 3000 });
      loading.value = False
    }
  }

  const startPolling = () => {
    taskProgress.value = 0;

    pollingInterval.value = setInterval(async () => {
      try {
        const res = await axios.get(`${import.meta.env.VITE_API_BASE_URL}/progress/${taskId.value}`);        
        taskStatus.value = res.data.status
        taskProgress.value = res.data.progress;

        if (res.data.status === 'completed') {
          clearInterval(pollingInterval.value);
          taskProgress.value = 100
          
          const result = await axios.get(`${import.meta.env.VITE_API_BASE_URL}/result/${taskId.value}`);          
          comparisonResults.value = result.data.comparison;
                    
          loading.value = false;
        }

        if (res.data.status === 'failed') {
          clearInterval(pollingInterval.value);
          loading.value = false;
          toast.add({ severity: 'error', summary: 'Processing failed', detail: 'Task failed during processing', life: 3000 });
        }        
      } catch (error) {
        clearInterval(pollingInterval.value);
        loading.value = false;
        console.error(error);
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to fetch task status', life: 3000 });
      }
    }, 1000); // Poll every 1 second
  };


  const generateTableHTML = () => {
    const htmlRows = comparisonResults.value.map(result => {
      const formatChunks = (chunks) => {
        if (typeof chunks === "string") {
          return `<span class="equal">${chunks}</span>`
        }
        return chunks.map(chunk => `<span class="${chunk.tag}">${chunk.subtext}</span>`).join('');
      }
        

      return `
        <tr>
          <td>${result.type}</td>
          <td>${result.ratio}</td>
          <td>${formatChunks(result.text_left_report)}</td>
          <td>${formatChunks(result.text_right_report)}</td>
          <td>${result.text_left_id}</td>
          <td>${result.text_right_id}</td>        
        </tr>
      `;
    }).join('');

    return `
      <!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8" />
        <title>Comparison Report</title>
        <style>
          table {
            border-collapse: collapse;
            width: 100%;
          }
          th, td {
            border: 1px solid #ccc;
            padding: 8px;
            text-align: left;
            vertical-align: top;
          }
          .equal { background-color: transparent; }
          .insert { background-color: #d4edda; }
          .delete { background-color: #f8d7da; }
          .replace { background-color: #fff3cd; }
          span { white-space: pre-wrap; }
        </style>
      </head>
      <body>
        <h1>Comparison Report</h1>
        <table>
          <thead>
            <tr>
              <th>Type</th>
              <th>Ratio</th>
              <th>Text Left</th>
              <th>Text Right</th>
              <th>ID # Left</th>
              <th>ID # Right</th>                             
            </tr>
          </thead>
          <tbody>
            ${htmlRows}
          </tbody>
        </table>
      </body>
      </html>
    `;
  }  
  
  const exportToExcel = () => {
    const worksheetData = comparisonResults.value.map(result => ({
      'Type': result.type,
      'Similarity Ratio': result.ratio,
      'Text Left': typeof result.text_left_report === "string" ? result.text_left_report : result.text_left_report.map(x => x.subtext).join(' '),
      'Text Right': typeof result.text_right_report === "string" ? result.text_right_report : result.text_right_report.map(x => x.subtext).join(' '),
      'ID # Left': result.text_left_id,
      'ID # Right': result.text_right_id
    }));
    const worksheet = XLSX.utils.json_to_sheet(worksheetData);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Comparison');
    XLSX.writeFile(workbook, 'comparison.xlsx');
  };

  const exportToHTML = () => {
    const tableHtml = generateTableHTML();
    const blob = new Blob([tableHtml], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'comparison_report.html';
    link.click();
    URL.revokeObjectURL(url);
  }; 
</script>

<style scoped>

:deep(.p-fileupload-choose-button) {
  background: #f1f5f9;
  color:black;
  border: 1px solid #f1f5f9;
  min-width: 8rem;
  max-width: 8rem;
}

:deep(.p-fileupload-choose-button:not(:disabled):hover) {
  background: #e2e9f1;
  color:black;
  border: 1px solid #e2e9f1;  
}

:deep(.p-fileupload) {
  flex-wrap: nowrap;
  justify-content: start;
  max-width: 24rem;
  min-width: 24rem;
}

:deep(.p-fileupload span) {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}

:deep(.p-datatable-column-filter-button) {
  display: none;
}

</style>