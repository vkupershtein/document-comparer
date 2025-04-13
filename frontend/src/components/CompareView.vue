<template>
  <Toast />
  <div class="max-w-screen-xl mx-auto">    
    <h1 class="text-2xl font-bold mb-6 ml-4">Doc Comparison Tool</h1>
    <form class="flex flex-col gap-2 justify-center items-start w-md mt-4 mb-4 ml-4" @submit.prevent="submitFiles">
      <FileUpload class="p-1 cursor-pointer" mode="basic" custom-upload  @select="handleFileUpload($event, 'left')" accept=".pdf,.xlsx" required />
      <Select v-if="leftHeaders.length" v-model="leftTextColumn" :options="leftHeaders" placeholder="Left: Select Text Column" class="mb-2" />
      <Select v-if="leftHeaders.length" v-model="leftIdColumn" :options="leftHeaders" placeholder="Left: Select ID Column (optional)" class="mb-2" />    
      <FileUpload class="p-1 cursor-pointer" mode="basic" custom-upload  @select="handleFileUpload($event, 'right')" accept=".pdf,.xlsx" required />
      <Select v-if="rightHeaders.length" v-model="rightTextColumn" :options="rightHeaders" placeholder="Left: Select Text Column" class="mb-2" />
      <Select v-if="rightHeaders.length" v-model="rightIdColumn" :options="rightHeaders" placeholder="Left: Select ID Column (optional)" class="mb-2" />      
      <Button class="w-50" label="Compare" severity="contrast" type="submit" />
    </form>

    <ProgressSpinner v-if="loading" style="width: 50px; height: 50px;" strokeWidth="8" fill="transparent" animationDuration=".5s" aria-label="Loading" />

    <DataTable v-if="comparisonResults.length > 0" 
      :value="comparisonResults"
      v-model:filters="filters"
      filterDisplay="row"
      :globalFilterFields="['text_left', 'text_right']"       
      paginator 
      :rows="100" 
      scrollable 
      scrollHeight="600px"
      :showFilterMenu="false" 
      :showFilterMatchModes="false"
      :showFilterOperator="false"
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
            :options="['same', 'changed', 'new', 'removed']"
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
      <Column field="heading_number_left" header="Heading # Original" />
      <Column field="heading_text_left" header="Heading Original" />                
      <Column field="heading_number_right" header="Heading # Updated" />
      <Column field="heading_text_right" header="Heading Updated" />        
    </DataTable>
  </div>
</template>
  
<script setup>
  import { ref } from 'vue';
  import { FilterMatchMode } from '@primevue/core/api'
  import axios from 'axios';
  import ProgressSpinner from 'primevue/progressspinner';
  import Toast from 'primevue/toast';
  import DataTable from 'primevue/datatable';
  import Column from 'primevue/column';
  import Button from 'primevue/button';  
  import InputText from 'primevue/inputtext';
  import FileUpload from 'primevue/fileupload';
  import { Select } from 'primevue';
  import { useToast } from 'primevue/usetoast';
  import FormattedText from '../components/FormattedText.vue';
  import * as XLSX from 'xlsx';  

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
    console.log('Submit');
    if (!leftFile.value || !rightFile.value) {
      toast.add({ severity: 'error', summary: 'File is not uploaded', detail: 'Please select both files', life: 3000 });
      return;
    }

    if ((leftHeaders.value.length > 0 && !leftTextColumn.value) || (rightHeaders.value.length > 0 && !rightTextColumn.value)) {
      toast.add({ severity: 'error', summary: 'Text column not present', detail: 'For Excel file text column must be selected', life: 3000 });
      return;      
    }

    loading.value = true;
      
    const formData = new FormData()
    formData.append('left_file', leftFile.value)
    formData.append('right_file', rightFile.value)

    formData.append('header_left', 40)
    formData.append('footer_left', 40)
    formData.append('size_weight_left', 0.8)
    formData.append('header_right', 40)
    formData.append('footer_right', 40)
    formData.append('size_weight_right', 0.8)
    formData.append('ratio_threshold', 0.5)
    formData.append('length_threshold', 30)

    formData.append('text_column_left', leftTextColumn.value)
    formData.append('id_column_left', leftIdColumn.value)
    formData.append('text_column_right', rightTextColumn.value)
    formData.append('id_column_right', rightIdColumn.value)
    
    console.log('Form data', formData);

    try {
      const response = await axios.post('http://127.0.0.1:8000/upload/', formData);
      comparisonResults.value = response.data.comparison;
    } catch (error) {
      console.error('Error uploading files:', error);
      toast.add({ severity: 'error', summary: 'Processing error', detail: 'Error occured while making comparison report', life: 3000 });
    } finally {
      loading.value = false;
    }
  }

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
          <td>${result.heading_number_left}</td>
          <td>${result.heading_text_left}</td>          
          <td>${result.heading_number_right}</td>          
          <td>${result.heading_text_right}</td>         
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
              <th>Heading # Left</th>
              <th>Heading Left</th>
              <th>Text Left</th>
              <th>Heading # Right</th>
              <th>Heading Right</th>
              <th>Text Right</th>                  
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
      'Heading # Left': result.heading_number_left,
      'Heading Left': result.heading_text_left,          
      'Heading # Right': result.heading_number_right,
      'Heading Right': result.heading_text_right
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
}

:deep(.p-fileupload-choose-button:not(:disabled):hover) {
  background: #e2e9f1;
  color:black;
  border: 1px solid #e2e9f1;  
}

:deep(.p-datatable-column-filter-button) {
  display: none;
}

</style>