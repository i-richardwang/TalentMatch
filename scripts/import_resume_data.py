import os
import sys
import json
from typing import Dict, List, Any

# Add project root directory to path
project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import asyncio
from utils.database.connections import MySQLConnectionManager
from backend.resume_management.storage.resume_repository import ResumeRepository
from backend.resume_management.storage.resume_vector_storage import store_resumes_batch_in_milvus, store_resumes_batch_in_milvus_async

def init_database():
    """Initialize database and tables"""
    try:
        ResumeRepository.init_all_tables()
        print("数据库表初始化成功")
    except Exception as e:
        print(f"初始化数据库时出错: {e}")

def load_json_data(file_path: str) -> List[Dict[str, Any]]:
    """Load JSON file data"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def merge_resume_data(resume_data: List[Dict], summary_data: List[Dict]) -> List[Dict]:
    """Merge resume data and summary data"""
    summary_dict = {}
    for item in summary_data:
        resume_id = item['id']
        # Handle data nested in ResumeSummary
        if 'ResumeSummary' in item:
            summary = item['ResumeSummary']
        else:
            summary = item
            
        # Use get method to safely retrieve fields with default values
        summary_dict[resume_id] = {
            'characteristics': summary.get('characteristics', ''),
            'experience': summary.get('experience', ''),
            'skills_overview': summary.get('skills_overview', '')
        }
    
    merged_data = []
    for resume in resume_data:
        try:
            resume_id = resume.get('id')
            if not resume_id:
                print(f"警告：跳过一条没有ID的简历数据")
                continue
                
            if resume_id in summary_dict:
                summary = summary_dict[resume_id]
                
                # Safely retrieve and process all fields
                personal_info = resume.get('personal_info', {})
                education = resume.get('education', [])
                work_experiences = resume.get('work_experiences', [])
                project_experiences = resume.get('project_experiences', [])
                
                merged_item = {
                    'resume_id': resume_id,
                    'personal_info': json.dumps(personal_info),
                    'education': json.dumps(education),
                    'work_experiences': json.dumps(work_experiences),
                    'project_experiences': json.dumps(project_experiences),
                    'characteristics': summary.get('characteristics', ''),
                    'experience_summary': summary.get('experience', ''),
                    'skills_overview': summary.get('skills_overview', ''),
                    'resume_format': 'json',
                    'file_or_url': 'data/datasets/merged_resume_json.json'
                }
                merged_data.append(merged_item)
            else:
                print(f"警告：简历ID {resume_id} 在摘要数据中未找到对应记录")
        except Exception as e:
            print(f"警告：处理简历时出错 (ID: {resume.get('id', 'unknown')}): {str(e)}")
            continue
    
    return merged_data

def import_to_database(data: List[Dict], batch_size: int = 500, 
                      import_mysql: bool = True, import_milvus: bool = True):
    """
    Import data to database with batch processing for better performance
    
    Args:
        data: List of resume data
        batch_size: Number of resumes to process in each batch (default: 500)
        import_mysql: Whether to import to MySQL (default: True)
        import_milvus: Whether to import to Milvus (default: True)
    """
    if not import_mysql and not import_milvus:
        print("⚠️  至少需要选择一个导入目标（MySQL 或 Milvus）")
        return
    try:
        # Convert key names to new format
        processed_data = []
        for item in data:
            processed_item = {
                'id': item['resume_id'],  # Convert key name
                'personal_info': json.loads(item['personal_info']) if isinstance(item['personal_info'], str) else item['personal_info'],
                'education': json.loads(item['education']) if isinstance(item['education'], str) else item['education'],
                'work_experiences': json.loads(item['work_experiences']) if isinstance(item['work_experiences'], str) else item['work_experiences'],
                'project_experiences': json.loads(item['project_experiences']) if isinstance(item['project_experiences'], str) else item['project_experiences'],
                'characteristics': item['characteristics'],
                'experience_summary': item['experience_summary'],
                'skills_overview': item['skills_overview'],
                'resume_format': item['resume_format'],
                'file_or_url': item['file_or_url']
            }
            processed_data.append(processed_item)
        
        print(f"\n开始批量导入，批次大小: {batch_size}")
        print(f"总数据量: {len(processed_data)} 条")
        print(f"预计批次数: {(len(processed_data) + batch_size - 1) // batch_size}")
        
        if import_mysql:
            print(f"✓ 将导入到 MySQL")
        if import_milvus:
            print(f"✓ 将导入到 Milvus")
        
        print("-" * 60)
        
        # Store to MySQL in batches
        mysql_success_count = 0
        if import_mysql:
            print("\n📊 第1阶段：批量导入到 MySQL...")
            
            for batch_idx in range(0, len(processed_data), batch_size):
                batch = processed_data[batch_idx:batch_idx + batch_size]
                batch_num = batch_idx // batch_size + 1
                total_batches = (len(processed_data) + batch_size - 1) // batch_size
                
                try:
                    success = ResumeRepository.batch_store_full_resumes(batch)
                    mysql_success_count += success
                    print(f"  批次 {batch_num}/{total_batches}: ✅ {success}/{len(batch)} 条")
                except Exception as e:
                    print(f"  批次 {batch_num}/{total_batches}: ❌ 失败 - {str(e)}")
            
            print(f"\n✅ MySQL批量导入完成: {mysql_success_count}/{len(processed_data)} 条")
            print("-" * 60)
        else:
            print("\n⊘ 跳过 MySQL 导入")
            print("-" * 60)
        
        # Store to Milvus vector database in batches
        vector_success_count = 0
        total_failed = []
        
        if import_milvus:
            print("\n🔍 第2阶段：批量导入到 Milvus 向量数据库 (使用异步加速⚡)...")
            
            async def process_all_batches():
                """Process all batches asynchronously"""
                nonlocal vector_success_count, total_failed
                
                for batch_idx in range(0, len(processed_data), batch_size):
                    batch = processed_data[batch_idx:batch_idx + batch_size]
                    batch_num = batch_idx // batch_size + 1
                    total_batches = (len(processed_data) + batch_size - 1) // batch_size
                    
                    print(f"\n  批次 {batch_num}/{total_batches} (简历 {batch_idx+1}-{min(batch_idx+batch_size, len(processed_data))})")
                    
                    try:
                        # Use async version for faster processing (10 concurrent requests)
                        success, failed = await store_resumes_batch_in_milvus_async(batch)
                        vector_success_count += success
                        total_failed.extend(failed)
                        
                        print(f"    ✅ 成功: {success}/{len(batch)} 条")
                        if failed:
                            print(f"    ⚠️  失败: {len(failed)} 条")
                            
                    except Exception as e:
                        print(f"    ❌ 批次处理失败: {str(e)}")
                        for item in batch:
                            total_failed.append({'id': item.get('id'), 'error': str(e)})
            
            # Run async processing
            asyncio.run(process_all_batches())
        else:
            print("\n⊘ 跳过 Milvus 向量导入")
        
        print("\n" + "=" * 60)
        print(f"📊 导入完成统计:")
        if import_mysql:
            print(f"  MySQL: {mysql_success_count}/{len(data)} 条")
        if import_milvus:
            print(f"  Milvus向量: {vector_success_count}/{len(data)} 条")
        
        if import_milvus and total_failed:
            print(f"\n⚠️  失败详情: {len(total_failed)} 条简历")
            print(f"  失败简历ID: {[f['id'] for f in total_failed[:10]]}")
            if len(total_failed) > 10:
                print(f"  ... 以及其他 {len(total_failed) - 10} 条")
        elif import_milvus and not total_failed:
            print(f"\n🎉 所有简历向量数据导入成功！")
        
        print("=" * 60)

    except Exception as e:
        print(f"导入数据时出错: {e}")

def main():
    import sys
    
    # Parse command line arguments for selective import
    import_mysql = True
    import_milvus = True
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode == 'mysql':
            import_milvus = False
            print("🎯 模式：仅导入 MySQL")
        elif mode == 'milvus':
            import_mysql = False
            print("🎯 模式：仅导入 Milvus")
        elif mode == 'all':
            print("🎯 模式：导入 MySQL + Milvus")
        else:
            print("⚠️  未知模式，使用默认（导入全部）")
            print("提示：使用 'mysql', 'milvus' 或 'all' 参数")
    else:
        print("🎯 模式：导入 MySQL + Milvus（默认）")
        print("提示：可使用参数指定模式 - python script.py [mysql|milvus|all]")
    
    print()
    
    # Initialize database
    init_database()

    try:
        # Load data
        print("正在加载简历数据...")
        resume_data = load_json_data('data/datasets/merged_resume_json.json')
        print(f"成功加载 {len(resume_data)} 条简历数据")
        
        print("正在加载简历摘要数据...")
        summary_data = load_json_data('data/datasets/resume_summary.json')
        print(f"成功加载 {len(summary_data)} 条摘要数据")

        # Merge data
        print("正在合并数据...")
        merged_data = merge_resume_data(resume_data, summary_data)
        print(f"成功合并 {len(merged_data)} 条数据")

        # Import to database with selected mode
        import_to_database(merged_data, import_mysql=import_mysql, import_milvus=import_milvus)
    except FileNotFoundError as e:
        print(f"错误：找不到数据文件 - {e}")
    except json.JSONDecodeError as e:
        print(f"错误：JSON 格式不正确 - {e}")
    except Exception as e:
        print(f"错误：处理数据时出现问题 - {e}")

if __name__ == "__main__":
    main() 